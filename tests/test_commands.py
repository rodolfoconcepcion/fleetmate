import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fleetmate.commands.client import COMMAND_SPECS, CommandResult, TeslaCommandExecutor
from fleetmate.mqtt.consumer import FleetMQTTConsumer
from fleetmate.mqtt.publisher import build_ha_discovery_payload


def test_command_specs_payloads() -> None:
    endpoint, fn = COMMAND_SPECS["climate_temp_f"]
    assert endpoint == "command/set_temps"
    # 70F -> 21.1C
    assert fn(70, None) == {"driver_temp": 21.1, "passenger_temp": 21.1}
    # Clamping bounds (59F..83F)
    assert fn(40, None) == {"driver_temp": 15.0, "passenger_temp": 15.0}
    assert fn(95, None) == {"driver_temp": 28.3, "passenger_temp": 28.3}

    ep_win, fn_win = COMMAND_SPECS["windows_vent"]
    assert ep_win == "command/window_control"
    assert fn_win(None, (25.7617, -80.1918)) == {
        "command": "vent",
        "lat": 25.7617,
        "lon": -80.1918,
    }

    ep_seat, fn_seat = COMMAND_SPECS["seat_heater_driver"]
    assert ep_seat == "command/remote_seat_heater_request"
    assert fn_seat(3, None) == {"seat_position": 0, "level": 3}

    ep_wheel, fn_wheel = COMMAND_SPECS["wheel_heater_on"]
    assert ep_wheel == "command/remote_steering_wheel_heater_request"
    assert fn_wheel(None, None) == {"on": True}


@pytest.mark.asyncio
async def test_execute_sends_signed_command(tmp_path) -> None:
    tok_path = tmp_path / "token.json"
    tok_path.write_text(json.dumps({"access_token": "tok-123", "expires_at": 9999999999}))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": {"result": True, "reason": ""}}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post.return_value = mock_resp

    executor = TeslaCommandExecutor(
        vin="5YJ3E1EA1PF000001",
        proxy_url="https://fleetmate-http-proxy:4445",
        token_file=str(tok_path),
    )

    with patch("fleetmate.commands.client.httpx.AsyncClient", return_value=mock_client):
        res = await executor.execute("charge_port_open")

    assert res.ok is True
    assert res.http_status == 200
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == (
        "https://fleetmate-http-proxy:4445/api/1/vehicles/5YJ3E1EA1PF000001/"
        "command/charge_port_door_open"
    )
    assert kwargs["headers"]["Authorization"] == "Bearer tok-123"


@pytest.mark.asyncio
async def test_execute_rejects_unknown_action(tmp_path) -> None:
    executor = TeslaCommandExecutor(vin="5YJ3E1EA1PF000001", token_file=str(tmp_path / "missing"))
    res = await executor.execute("self_destruct")
    assert res.ok is False
    assert "Unsupported action" in res.message


def test_ha_discovery_includes_command_components() -> None:
    payload = build_ha_discovery_payload(
        car_id=1,
        vehicle_name="TestEV",
        vehicle_model="Model 3",
        prefix="fleetmate",
        public_url="https://fleetmate.example.invalid",
    )
    components = payload["components"]
    for expected_key, expected_platform in (
        ("door_lock", "lock"),
        ("sentry_control", "switch"),
        ("charging_control", "switch"),
        ("climate_control", "switch"),
        ("charge_port_control", "switch"),
        ("steering_wheel_heater", "switch"),
        ("charge_limit_target", "number"),
        ("charge_amps_target", "number"),
        ("cabin_temp_target", "number"),
        ("seat_heater_driver", "number"),
        ("seat_heater_passenger", "number"),
        ("vent_windows", "button"),
        ("close_windows", "button"),
        ("open_frunk", "button"),
        ("open_trunk", "button"),
        ("flash_lights", "button"),
        ("honk_horn", "button"),
        ("wake_up", "button"),
        ("install_software_update", "button"),
    ):
        assert components[expected_key]["platform"] == expected_platform
        assert "/cmd/" in components[expected_key]["command_topic"]


@pytest.mark.asyncio
async def test_mqtt_consumer_dispatches_ha_commands() -> None:
    engine = MagicMock()
    engine.publisher = None
    engine.last_coords = (25.76, -80.19)

    publisher = MagicMock()
    publisher.publish_raw = AsyncMock()

    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=CommandResult(ok=True, action="ok", message="OK", http_status=200)
    )

    consumer = FleetMQTTConsumer(engine=engine, publisher=publisher, command_executor=executor)

    await consumer._dispatch_command("door_lock", "LOCK")
    executor.execute.assert_awaited_with("lock", value=None, coords=(25.76, -80.19))
    publisher.publish_raw.assert_awaited_with("locked", "true", retain=True)

    await consumer._dispatch_command("cabin_temp_f", "71")
    executor.execute.assert_awaited_with("climate_temp_f", value=71.0, coords=(25.76, -80.19))
    publisher.publish_raw.assert_awaited_with("cabin_temp_target_f", "71", retain=True)

    await consumer._dispatch_command("windows_vent", "PRESS")
    executor.execute.assert_awaited_with("windows_vent", value=None, coords=(25.76, -80.19))


@pytest.mark.asyncio
async def test_execute_invalid_numeric_value_and_wake_response(tmp_path: Path) -> None:
    import httpx

    tok_file = tmp_path / "token.json"
    tok_file.write_text('{"access_token": "tok123", "expires_at": 9999999999}')
    executor = TeslaCommandExecutor(
        vin="5YJ3E1EBXRF822141",
        proxy_url="https://proxy.example.invalid",
        token_file=str(tok_file),
    )

    mock_client = MagicMock()
    mock_client.post = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(httpx, "AsyncClient", return_value=mock_client):
        res_bad = await executor.execute("charge_limit", value=None)
        assert res_bad.ok is False
        mock_client.post.assert_not_called()

        wake_resp = MagicMock()
        wake_resp.status_code = 200
        wake_resp.json.return_value = {"response": {"state": "online"}}
        mock_client.post = AsyncMock(return_value=wake_resp)

        res_wake = await executor.execute("wake")
        assert res_wake.ok is True
        assert res_wake.message == "online"

        res_non_wake = await executor.execute("flash_lights")
        assert res_non_wake.ok is False


@pytest.mark.asyncio
async def test_cancel_flush_tasks_clears_command_tasks() -> None:
    import asyncio

    engine = MagicMock()
    engine.publisher = None
    engine.last_coords = None
    started = asyncio.Event()

    async def _blocking_execute(*_args: Any, **_kwargs: Any) -> CommandResult:
        started.set()
        await asyncio.sleep(10)
        return CommandResult(ok=True, action="wake", message="OK")

    executor = MagicMock()
    executor.execute = AsyncMock(side_effect=_blocking_execute)

    consumer = FleetMQTTConsumer(engine=engine, publisher=None, command_executor=executor)
    msg = MagicMock()
    msg.topic = f"{consumer._cmd_prefix}wake"
    msg.payload = b"PRESS"

    await consumer._handle_message(msg)
    await started.wait()
    assert len(consumer._command_tasks) == 1
    task = next(iter(consumer._command_tasks))

    await consumer._cancel_flush_tasks()
    assert len(consumer._command_tasks) == 0
    assert task.cancelled()


def test_charging_control_value_template_matches_active_states() -> None:
    payload = build_ha_discovery_payload(
        car_id=1,
        prefix="fleetmate",
        vehicle_name="Wilfrido",
        vehicle_model="Model 3",
        public_url="https://fleetmate.example.invalid/",
    )
    tpl = payload["components"]["charging_control"]["value_template"]
    for active in (
        "Charging",
        "Starting",
        "DetailedChargeStateCharging",
        "DetailedChargeStateStarting",
    ):
        assert active in tpl
    assert "Stopped" not in tpl

