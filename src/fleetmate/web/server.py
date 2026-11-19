"""Zero-dependency asyncio HTTP/1.1 + REST API + Leaflet Web UI server for FleetMate."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs, urlsplit

import orjson

from fleetmate.commands.client import TeslaCommandExecutor
from fleetmate.config.settings import Settings
from fleetmate.config.settings import settings as default_settings
from fleetmate.state.engine import StateMachineEngine
from fleetmate.storage.postgres import FleetMateRepository
from fleetmate.web.ui import PORTAL_HTML

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024
GEOFENCE_ID_RE = re.compile(r"^/api/geofences/(\d+)$")


class FleetMateWebServer:
    """Asyncio HTTP server exposing GeoLoc UI, Places/Geo-Fences CRUD, and command API."""

    def __init__(
        self,
        repo: FleetMateRepository,
        engine: StateMachineEngine,
        command_executor: TeslaCommandExecutor | None = None,
        config: Settings | None = None,
    ) -> None:
        self.repo = repo
        self.engine = engine
        self.command_executor = command_executor
        self.config = config or default_settings
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        """Start listening on configured host and port."""
        self._server = await asyncio.start_server(
            self._handle_client, self.config.host, self.config.port
        )
        addrs = ", ".join(str(sock.getsockname()) for sock in (self._server.sockets or []))
        logger.info("FleetMate Web Portal listening on %s", addrs or self.config.port)

    async def stop(self) -> None:
        """Stop accepting new connections and close server cleanly."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("FleetMate Web Portal stopped.")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            method, target, body = await self._read_http_request(reader)
            if method is None:
                return
            status, ctype, payload = await self.dispatch(method, target, body)
            await self._write_http_response(writer, status, ctype, payload)
        except TimeoutError:
            with contextlib.suppress(Exception):
                await self._write_json(writer, 408, {"error": "Request timeout"})
        except ValueError as err:
            with contextlib.suppress(Exception):
                await self._write_json(writer, 400, {"error": str(err)})
        except Exception as err:
            logger.exception("Unhandled Web Portal error: %s", err)
            with contextlib.suppress(Exception):
                await self._write_json(writer, 500, {"error": "Internal server error"})
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    @staticmethod
    async def _read_http_request(
        reader: asyncio.StreamReader,
    ) -> tuple[str | None, str, bytes]:
        request_line_raw = await asyncio.wait_for(reader.readline(), timeout=15.0)
        if not request_line_raw:
            return None, "", b""
        request_line = request_line_raw.decode("latin-1").strip()
        parts = request_line.split(" ", 2)
        if len(parts) < 2:
            raise ValueError("Malformed HTTP request line")
        method = parts[0].upper()
        target = parts[1]

        headers: dict[str, str] = {}
        for _ in range(128):
            line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if line in (b"\r\n", b"\n", b""):
                break
            decoded = line.decode("latin-1").rstrip("\r\n")
            if ":" in decoded:
                k, v = decoded.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        content_length = int(headers.get("content-length", "0") or "0")
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            raise ValueError("Invalid Content-Length")
        body = (
            await asyncio.wait_for(reader.readexactly(content_length), timeout=15.0)
            if content_length > 0
            else b""
        )
        return method, target, body

    @staticmethod
    async def _write_http_response(
        writer: asyncio.StreamWriter, status: int, content_type: str, body: bytes
    ) -> None:
        phrase = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "OK"
        header = (
            f"HTTP/1.1 {status} {phrase}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        writer.write(header + body)
        await writer.drain()

    async def _write_json(
        self, writer: asyncio.StreamWriter, status: int, data: dict[str, Any]
    ) -> None:
        await self._write_http_response(
            writer, status, "application/json; charset=utf-8", orjson.dumps(data)
        )

    @staticmethod
    def _json_response(status: int, data: dict[str, Any]) -> tuple[int, str, bytes]:
        return status, "application/json; charset=utf-8", orjson.dumps(data)

    @staticmethod
    def _parse_json_body(body: bytes) -> dict[str, Any]:
        if not body:
            return {}
        try:
            parsed = orjson.loads(body)
        except orjson.JSONDecodeError as err:
            raise ValueError("Invalid JSON payload") from err
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    @staticmethod
    def _validate_geofence_fields(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if not partial or "name" in data:
            name = str(data.get("name", "")).strip()
            if not name:
                raise ValueError("Geo-fence name is required")
            out["name"] = name[:255]
        if not partial or "latitude" in data:
            lat = float(data["latitude"])
            if not (-90.0 <= lat <= 90.0):
                raise ValueError("Latitude must be between -90 and 90")
            out["latitude"] = lat
        if not partial or "longitude" in data:
            lon = float(data["longitude"])
            if not (-180.0 <= lon <= 180.0):
                raise ValueError("Longitude must be between -180 and 180")
            out["longitude"] = lon
        if "radius" in data or not partial:
            radius = int(data.get("radius", 25))
            if not (5 <= radius <= 5000):
                raise ValueError("Radius must be between 5 and 5000 meters")
            out["radius"] = radius
        if "billing_type" in data or not partial:
            bt = str(data.get("billing_type", "per_kwh"))
            if bt not in ("per_kwh", "per_minute"):
                raise ValueError("billing_type must be per_kwh or per_minute")
            out["billing_type"] = bt
        if "cost_per_unit" in data or not partial:
            raw = data.get("cost_per_unit")
            out["cost_per_unit"] = float(raw) if raw not in (None, "") else None
        if "session_fee" in data or not partial:
            raw = data.get("session_fee")
            out["session_fee"] = float(raw) if raw not in (None, "") else None
        return out

    async def dispatch(
        self, method: str, target: str, body: bytes = b""
    ) -> tuple[int, str, bytes]:
        """Route an HTTP request and return (status, content_type, body_bytes)."""
        split = urlsplit(target)
        path = split.path or "/"
        qs = parse_qs(split.query)

        if method == "GET" and path == "/health":
            return self._json_response(200, {"status": "ok"})

        if method == "GET" and path in ("/", "/index.html"):
            return 200, "text/html; charset=utf-8", PORTAL_HTML.encode("utf-8")

        if method == "GET" and path == "/api/snapshot":
            snap = await self.repo.get_live_snapshot(self.config.car_id)
            positions = await self.repo.list_recent_positions(self.config.car_id, 120)
            snap["positions"] = positions
            snap["live_state"] = self.engine.current_state
            snap["grafana_url"] = self.config.grafana_url
            if self.engine.current_geofence_name and not snap.get("matched_geofence"):
                snap["matched_geofence"] = {"id": None, "name": self.engine.current_geofence_name}
            return self._json_response(200, snap)

        if path == "/api/geofences":
            if method == "GET":
                rows = await self.repo.list_geofences()
                return self._json_response(200, {"geofences": rows})
            if method == "POST":
                data = self._validate_geofence_fields(self._parse_json_body(body), partial=False)
                row = await self.repo.create_geofence(**data)
                return self._json_response(201, {"geofence": row})

        match = GEOFENCE_ID_RE.match(path)
        if match:
            gf_id = int(match.group(1))
            if method == "PUT":
                data = self._validate_geofence_fields(self._parse_json_body(body), partial=True)
                updated_row = await self.repo.update_geofence(gf_id, **data)
                if updated_row is None:
                    return self._json_response(404, {"error": "Geo-fence not found"})
                return self._json_response(200, {"geofence": updated_row})
            if method == "DELETE":
                deleted = await self.repo.delete_geofence(gf_id)
                if not deleted:
                    return self._json_response(404, {"error": "Geo-fence not found"})
                return self._json_response(200, {"deleted": True})

        if method == "GET" and path == "/api/places":
            limit = int(qs.get("limit", ["200"])[0])
            rows = await self.repo.list_places(limit=limit)
            return self._json_response(200, {"places": rows})

        if method == "GET" and path == "/api/drives":
            limit = int(qs.get("limit", ["25"])[0])
            rows = await self.repo.list_recent_drives(self.config.car_id, limit=limit)
            return self._json_response(200, {"drives": rows})

        if method == "GET" and path == "/api/charges":
            limit = int(qs.get("limit", ["25"])[0])
            rows = await self.repo.list_recent_charges(self.config.car_id, limit=limit)
            return self._json_response(200, {"charges": rows})

        if method == "POST" and path == "/api/command":
            if self.command_executor is None:
                return self._json_response(503, {"ok": False, "message": "Command executor disabled"})
            payload = self._parse_json_body(body)
            action = str(payload.get("action", "")).strip()
            if not action:
                return self._json_response(400, {"ok": False, "message": "action is required"})
            res = await self.command_executor.execute(
                action, value=payload.get("value"), coords=self.engine.last_coords
            )
            return self._json_response(
                200 if res.ok else (res.http_status or 400),
                {
                    "ok": res.ok,
                    "action": res.action,
                    "status_code": res.http_status,
                    "message": res.message,
                },
            )

        return self._json_response(404, {"error": "Not found"})
