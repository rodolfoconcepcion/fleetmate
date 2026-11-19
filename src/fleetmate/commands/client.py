import asyncio
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from fleetmate.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CommandResult:
    ok: bool
    action: str
    message: str
    http_status: int | None = None


CoordPair = tuple[float | Decimal, float | Decimal]
PayloadBuilder = Callable[[Any, CoordPair | None], dict[str, Any]]


def _f_to_c(fahrenheit: float) -> float:
    return round((fahrenheit - 32.0) * 5.0 / 9.0, 1)


def _window_payload(command: str, coords: CoordPair | None) -> dict[str, Any]:
    lat, lon = (float(coords[0]), float(coords[1])) if coords is not None else (0.0, 0.0)
    return {"command": command, "lat": lat, "lon": lon}


COMMAND_SPECS: dict[str, tuple[str, PayloadBuilder]] = {
    "wake": ("wake_up", lambda _v, _c: {}),
    "lock": ("command/door_lock", lambda _v, _c: {}),
    "unlock": ("command/door_unlock", lambda _v, _c: {}),
    "sentry_on": ("command/set_sentry_mode", lambda _v, _c: {"on": True}),
    "sentry_off": ("command/set_sentry_mode", lambda _v, _c: {"on": False}),
    "charge_start": ("command/charge_start", lambda _v, _c: {}),
    "charge_stop": ("command/charge_stop", lambda _v, _c: {}),
    "charge_port_open": ("command/charge_port_door_open", lambda _v, _c: {}),
    "charge_port_close": ("command/charge_port_door_close", lambda _v, _c: {}),
    "charge_limit": (
        "command/set_charge_limit",
        lambda v, _c: {"percent": max(50, min(100, int(round(float(v)))))},
    ),
    "charge_amps": (
        "command/set_charging_amps",
        lambda v, _c: {"charging_amps": max(5, min(48, int(round(float(v)))))},
    ),
    "climate_on": ("command/auto_conditioning_start", lambda _v, _c: {}),
    "climate_off": ("command/auto_conditioning_stop", lambda _v, _c: {}),
    "climate_temp_f": (
        "command/set_temps",
        lambda v, _c: (lambda c: {"driver_temp": c, "passenger_temp": c})(
            _f_to_c(max(59.0, min(83.0, float(v))))
        ),
    ),
    "wheel_heater_on": ("command/remote_steering_wheel_heater_request", lambda _v, _c: {"on": True}),
    "wheel_heater_off": (
        "command/remote_steering_wheel_heater_request",
        lambda _v, _c: {"on": False},
    ),
    "seat_heater_driver": (
        "command/remote_seat_heater_request",
        lambda v, _c: {"seat_position": 0, "level": max(0, min(3, int(round(float(v)))))},
    ),
    "seat_heater_passenger": (
        "command/remote_seat_heater_request",
        lambda v, _c: {"seat_position": 1, "level": max(0, min(3, int(round(float(v)))))},
    ),
    "windows_vent": ("command/window_control", lambda _v, c: _window_payload("vent", c)),
    "windows_close": ("command/window_control", lambda _v, c: _window_payload("close", c)),
    "open_frunk": ("command/actuate_trunk", lambda _v, _c: {"which_trunk": "front"}),
    "open_trunk": ("command/actuate_trunk", lambda _v, _c: {"which_trunk": "rear"}),
    "flash_lights": ("command/flash_lights", lambda _v, _c: {}),
    "honk_horn": ("command/honk_horn", lambda _v, _c: {}),
    "schedule_software_update": (
        "command/schedule_software_update",
        lambda v, _c: {"offset_sec": max(0, int(round(float(v or 0))))},
    ),
}


class TeslaCommandExecutor:
    """Executes signed Tesla Fleet API commands via fleetmate-http-proxy."""

    def __init__(
        self,
        vin: str = settings.vin,
        proxy_url: str = settings.fleet_proxy_url,
        token_file: str = settings.fleet_token_file,
        auth_url: str = settings.fleet_auth_url,
        client_id: str = settings.fleet_client_id,
        client_secret: str = settings.fleet_client_secret,
        proxy_verify_ssl: bool = settings.fleet_proxy_verify_ssl,
        proxy_ca_cert: str | None = settings.fleet_proxy_ca_cert,
    ) -> None:
        self.vin = vin
        self.proxy_url = proxy_url.rstrip("/")
        self.token_file = token_file
        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.proxy_verify_ssl: bool | str = proxy_ca_cert if proxy_ca_cert else proxy_verify_ssl
        self._token_lock = asyncio.Lock()
        self._cached_token: tuple[str, int] | None = None

    def _read_token_file(self) -> dict[str, Any] | None:
        if not os.path.exists(self.token_file):
            return None
        with open(self.token_file) as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else None

    def _write_token_file(self, token_data: dict[str, Any]) -> None:
        tmp = f"{self.token_file}.tmp"
        with open(tmp, "w") as f:
            json.dump(token_data, f, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.token_file)

    async def _get_access_token(self) -> str | None:
        async with self._token_lock:
            now = int(time.time())
            if self._cached_token is not None:
                tok, exp = self._cached_token
                if tok and exp > now + 900:
                    return tok

            try:
                data = await asyncio.to_thread(self._read_token_file)
            except Exception as exc:
                logger.warning("Failed reading token file %s: %s", self.token_file, exc)
                data = None

            if not data:
                return self._cached_token[0] if self._cached_token else None

            exp = int(data.get("expires_at") or 0)
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")

            if access_token and exp > now + 900:
                self._cached_token = (str(access_token), exp)
                return str(access_token)

            if refresh_token and self.client_id:
                form: dict[str, str] = {
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "refresh_token": str(refresh_token),
                }
                if self.client_secret:
                    form["client_secret"] = self.client_secret
                try:
                    async with httpx.AsyncClient(verify=True, timeout=15.0) as auth_client:
                        resp = await auth_client.post(self.auth_url, data=form)
                    if resp.status_code == 200:
                        new_tok = resp.json()
                        new_access = new_tok.get("access_token")
                        if new_access:
                            new_exp = now + int(new_tok.get("expires_in", 28800))
                            new_tok["expires_at"] = new_exp
                            new_tok["updated_at"] = now
                            self._cached_token = (str(new_access), new_exp)
                            try:
                                await asyncio.to_thread(self._write_token_file, new_tok)
                            except Exception as write_exc:
                                logger.warning(
                                    "OAuth token refreshed in memory but persistence failed: %s",
                                    write_exc,
                                )
                            return str(new_access)
                except Exception as exc:
                    logger.warning("OAuth token refresh failed: %s", exc)

            return str(access_token) if access_token else None

    async def execute(
        self,
        action: str,
        value: Any = None,
        coords: CoordPair | None = None,
    ) -> CommandResult:
        spec = COMMAND_SPECS.get(action)
        if spec is None:
            return CommandResult(ok=False, action=action, message=f"Unsupported action: {action}")
        if not self.vin:
            return CommandResult(ok=False, action=action, message="Vehicle VIN not configured")

        endpoint, build_payload = spec
        payload = build_payload(value, coords)
        url = f"{self.proxy_url}/api/1/vehicles/{self.vin}/{endpoint}"

        try:
            token = await self._get_access_token()
            if not token:
                return CommandResult(
                    ok=False, action=action, message="Missing or invalid Fleet API token"
                )
            async with httpx.AsyncClient(verify=self.proxy_verify_ssl, timeout=20.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
        except Exception as exc:
            logger.error("Command %s transport error: %s", action, exc)
            return CommandResult(ok=False, action=action, message=str(exc))

        if resp.status_code >= 400:
            err_msg = resp.text[:240]
            logger.warning("Command %s HTTP %s: %s", action, resp.status_code, err_msg)
            return CommandResult(
                ok=False, action=action, message=err_msg, http_status=resp.status_code
            )

        try:
            raw_json = resp.json()
        except Exception:
            return CommandResult(
                ok=False,
                action=action,
                message="Unexpected non-JSON response from proxy",
                http_status=resp.status_code,
            )

        body = raw_json.get("response") if isinstance(raw_json, dict) else None
        if isinstance(body, dict) and "result" in body:
            ok = bool(body.get("result"))
            reason = str(body.get("reason") or ("OK" if ok else "Rejected"))
            return CommandResult(ok=ok, action=action, message=reason, http_status=resp.status_code)
        return CommandResult(
            ok=False,
            action=action,
            message="Unexpected proxy response format",
            http_status=resp.status_code,
        )
