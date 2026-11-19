from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from fleetmate.commands.client import CommandResult
from fleetmate.config.settings import Settings
from fleetmate.web.server import FleetMateWebServer


def _make_server() -> tuple[FleetMateWebServer, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.list_geofences = AsyncMock(
        return_value=[{"id": 1, "name": "Home", "latitude": 25.76, "longitude": -80.19, "radius": 30}]
    )
    repo.create_geofence = AsyncMock(
        return_value={"id": 2, "name": "Office", "latitude": 25.78, "longitude": -80.21, "radius": 40}
    )
    repo.update_geofence = AsyncMock(
        return_value={"id": 1, "name": "Home Updated", "latitude": 25.76, "longitude": -80.19, "radius": 35}
    )
    repo.delete_geofence = AsyncMock(return_value=True)
    repo.list_places = AsyncMock(return_value=[{"id": 10, "display_name": "Main St"}])
    repo.list_recent_drives = AsyncMock(return_value=[{"id": 5, "distance": 12.4}])
    repo.list_recent_charges = AsyncMock(return_value=[{"id": 7, "charge_energy_added": 22.1}])
    repo.get_live_snapshot = AsyncMock(
        return_value={"car": {"id": 1, "name": "TestEV"}, "position": {"battery_level": 80}, "counts": {}}
    )
    repo.list_recent_positions = AsyncMock(return_value=[{"id": 99, "latitude": 25.76, "longitude": -80.19}])

    engine = MagicMock()
    engine.current_state = "online"
    engine.current_geofence_name = "Home"
    engine.last_coords = (25.76, -80.19)

    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=CommandResult(ok=True, action="flash_lights", message="OK", http_status=200)
    )

    cfg = Settings(car_id=1, grafana_url="https://grafana.example.invalid", web_api_token=None)
    server = FleetMateWebServer(repo=repo, engine=engine, command_executor=executor, config=cfg)
    return server, repo, executor


@pytest.mark.asyncio
async def test_web_health_and_ui() -> None:
    server, _, _ = _make_server()
    status, ctype, body = await server.dispatch("GET", "/health")
    assert status == 200
    assert "application/json" in ctype
    assert orjson.loads(body) == {"status": "ok"}

    status_ui, ctype_ui, body_ui = await server.dispatch("GET", "/")
    assert status_ui == 200
    assert "text/html" in ctype_ui
    assert b"GeoLoc Map" in body_ui
    assert b"Geo-Fences" in body_ui


@pytest.mark.asyncio
async def test_web_geofence_crud_and_snapshot() -> None:
    server, repo, _ = _make_server()

    status, _, body = await server.dispatch("GET", "/api/snapshot")
    assert status == 200
    snap = orjson.loads(body)
    assert snap["live_state"] == "online"
    assert snap["grafana_url"] == "https://grafana.example.invalid"

    status, _, body = await server.dispatch(
        "POST",
        "/api/geofences",
        orjson.dumps({"name": "Office", "latitude": 25.78, "longitude": -80.21, "radius": 40}),
    )
    assert status == 201
    assert orjson.loads(body)["geofence"]["name"] == "Office"
    repo.create_geofence.assert_awaited_once()

    status, _, body = await server.dispatch(
        "PUT",
        "/api/geofences/1",
        orjson.dumps({"name": "Home Updated", "radius": 35}),
    )
    assert status == 200
    assert orjson.loads(body)["geofence"]["name"] == "Home Updated"

    status, _, body = await server.dispatch("DELETE", "/api/geofences/1")
    assert status == 200
    assert orjson.loads(body) == {"deleted": True}


@pytest.mark.asyncio
async def test_web_validation_and_command_execution() -> None:
    server, _, executor = _make_server()

    with pytest.raises(ValueError, match="Latitude"):
        await server.dispatch(
            "POST",
            "/api/geofences",
            orjson.dumps({"name": "Bad", "latitude": 120.0, "longitude": 0.0, "radius": 25}),
        )

    status, _, body = await server.dispatch(
        "POST",
        "/api/command",
        orjson.dumps({"action": "flash_lights"}),
    )
    assert status == 200
    assert orjson.loads(body)["ok"] is True
    executor.execute.assert_awaited_once_with(
        "flash_lights", value=None, coords=(25.76, -80.19)
    )


def test_web_bearer_auth_check() -> None:
    server, _, _ = _make_server()
    assert server._is_authorized({}) is True

    server.config = server.config.model_copy(update={"web_api_token": "secret-token"})
    assert server._is_authorized({}) is False
    assert server._is_authorized({"authorization": "Bearer wrong"}) is False
    assert server._is_authorized({"authorization": "Bearer secret-token"}) is True
