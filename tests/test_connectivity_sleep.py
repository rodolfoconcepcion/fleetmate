import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from fleetmate.mqtt.consumer import FleetMQTTConsumer
from fleetmate.state.engine import StateMachineEngine, VehicleState
from fleetmate.telemetry.models import VehicleTelemetryPoint


def _make_engine_and_consumer(sleep_debounce: float = 0.05):
    repo = MagicMock()
    repo.find_geofence = AsyncMock(return_value=None)
    publisher = MagicMock()
    publisher.publish_state_only = AsyncMock()
    publisher.publish_point = AsyncMock()
    engine = StateMachineEngine(repo=repo, publisher=publisher)
    consumer = FleetMQTTConsumer(
        engine=engine,
        publisher=publisher,
        debounce_seconds=0.0,
        sleep_debounce_seconds=sleep_debounce,
    )
    return engine, publisher, consumer


@pytest.mark.asyncio
async def test_connectivity_disconnect_marks_asleep_after_debounce():
    engine, publisher, consumer = _make_engine_and_consumer(sleep_debounce=0.02)
    vin = "5YJ3E1EBXRF822141"

    await consumer._handle_connectivity(vin, {"NetworkInterface": "wifi", "Status": "CONNECTED"})
    assert engine.current_state == VehicleState.ONLINE

    await consumer._handle_connectivity(vin, {"NetworkInterface": "wifi", "Status": "DISCONNECTED"})
    task = consumer._sleep_tasks[vin]
    await task

    assert engine.current_state == VehicleState.ASLEEP
    publisher.publish_state_only.assert_awaited()
    assert publisher.publish_state_only.await_args.args[0] == "asleep"


@pytest.mark.asyncio
async def test_connectivity_handoff_cancels_sleep():
    engine, publisher, consumer = _make_engine_and_consumer(sleep_debounce=0.5)
    vin = "5YJ3E1EBXRF822141"

    await consumer._handle_connectivity(vin, {"NetworkInterface": "wifi", "Status": "DISCONNECTED"})
    task = consumer._sleep_tasks[vin]
    await consumer._handle_connectivity(vin, {"NetworkInterface": "cellular", "Status": "CONNECTED"})
    await asyncio.gather(task, return_exceptions=True)

    assert vin not in consumer._sleep_tasks
    assert task.cancelled()
    assert engine.current_state == VehicleState.ONLINE
    publisher.publish_state_only.assert_not_called()


@pytest.mark.asyncio
async def test_telemetry_point_wakes_asleep_engine():
    engine, publisher, _ = _make_engine_and_consumer()
    await engine.mark_asleep()
    assert engine.current_state == VehicleState.ASLEEP

    point = VehicleTelemetryPoint(
        vin="5YJ3E1EBXRF822141",
        timestamp=datetime.now(UTC),
        battery_level=50,
    )
    await engine.process_point(point)

    assert engine.current_state == VehicleState.ONLINE
    publisher.publish_point.assert_awaited_once()
