import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from fleetmate.mqtt.publisher import StateMQTTPublisher, build_ha_discovery_payload
from fleetmate.state.engine import StateMachineEngine
from fleetmate.telemetry.models import VehicleTelemetryPoint


def test_build_ha_discovery_payload_uses_fleetmate_namespace():
    payload = build_ha_discovery_payload(
        car_id=1,
        prefix="fleetmate",
        vehicle_name="Demo Car",
        vehicle_model="Model 3",
        public_url="https://fleetmate.example.com/",
    )
    assert payload["device"]["identifiers"] == ["fleetmate_car_1"]
    assert payload["device"]["configuration_url"] == "https://fleetmate.example.com/"
    assert payload["origin"]["name"] == "FleetMate"
    components = payload["components"]
    assert components["battery_level"]["state_topic"] == "fleetmate/cars/1/battery_level"
    assert components["battery_level"]["unique_id"] == "fleetmate_1_battery_level"
    assert components["charging"]["state_topic"] == "fleetmate/cars/1/charging_state"
    assert components["location"]["json_attributes_topic"] == "fleetmate/cars/1/location"
    serialized = json.dumps(payload).lower()
    assert "teslamate" not in serialized


@pytest.mark.asyncio
async def test_publisher_publishes_discovery_and_state_messages():
    client = AsyncMock()
    publisher = StateMQTTPublisher(
        car_id=1,
        prefix="fleetmate",
        ha_prefix="homeassistant",
        ha_discovery_enabled=True,
        enabled=True,
        vehicle_name="Demo Car",
        vehicle_model="Model 3",
        public_url="https://fleetmate.example.com/",
    )
    publisher.set_client(client)
    await publisher.publish_discovery()

    published_topics = [call.args[0] for call in client.publish.call_args_list]
    assert "homeassistant/device/fleetmate_1/config" in published_topics
    assert "fleetmate/cars/1/display_name" in published_topics
    assert "fleetmate/cars/1/healthy" in published_topics

    client.publish.reset_mock()
    point = VehicleTelemetryPoint.from_fleet_telemetry_json(
        "5YJ3E1EA1PF000001",
        {
            "Location": {"latitude": 39.7817, "longitude": -89.6501},
            "VehicleSpeed": 45,
            "Power": 18,
            "Soc": 77,
            "RatedRange": 380.5,
            "Odometer": 15420.5,
            "Gear": "D",
            "Locked": True,
            "DoorState": {"DriverFront": False, "PassengerFront": False},
            "SentryMode": True,
            "ChargeLimitSoc": 80,
            "TpmsPressureFl": 2.9,
        },
    ).model_copy(update={"timestamp": datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)})

    await publisher.publish_point(point, vehicle_state="driving", geofence_name="Home")
    published = {call.args[0]: call.args[1] for call in client.publish.call_args_list}
    assert published["fleetmate/cars/1/state"] == "driving"
    assert published["fleetmate/cars/1/since"] == "2026-11-15T12:00:00Z"
    assert published["fleetmate/cars/1/battery_level"] == "77"
    assert published["fleetmate/cars/1/speed"] == "45"
    assert published["fleetmate/cars/1/locked"] == "true"
    assert published["fleetmate/cars/1/doors_open"] == "false"
    assert published["fleetmate/cars/1/sentry_mode"] == "true"
    assert published["fleetmate/cars/1/charge_limit_soc"] == "80"
    assert published["fleetmate/cars/1/geofence"] == "Home"
    assert json.loads(published["fleetmate/cars/1/location"]) == {
        "latitude": 39.7817,
        "longitude": -89.6501,
    }


@pytest.mark.asyncio
async def test_state_engine_forwards_points_to_publisher():
    repo = AsyncMock()
    repo.insert_position.return_value = 101
    repo.start_drive.return_value = 202
    repo.find_geofence.return_value = None
    geocoder = AsyncMock()
    geocoder.reverse_geocode.return_value = None

    publisher = StateMQTTPublisher(car_id=1, prefix="fleetmate", enabled=True)
    client = AsyncMock()
    publisher.set_client(client)

    engine = StateMachineEngine(repo=repo, car_id=1, geocoder=geocoder, publisher=publisher)
    point = VehicleTelemetryPoint(
        vin="5YJ3E1EA1PF000001",
        timestamp=datetime(2026, 11, 15, 12, 5, 0, tzinfo=UTC),
        latitude=Decimal("39.7817"),
        longitude=Decimal("-89.6501"),
        speed=50,
        gear="D",
        battery_level=72,
    )
    await engine.process_point(point)

    published = {call.args[0]: call.args[1] for call in client.publish.call_args_list}
    assert published["fleetmate/cars/1/state"] == "driving"
    assert published["fleetmate/cars/1/battery_level"] == "72"


@pytest.mark.asyncio
async def test_consumer_coalesces_per_field_topics_and_converts_miles_to_km():
    from types import SimpleNamespace

    from fleetmate.mqtt.consumer import FleetMQTTConsumer

    engine = AsyncMock()
    engine.publisher = None
    consumer = FleetMQTTConsumer(engine=engine, debounce_seconds=0.05)

    def msg(topic: str, payload: bytes) -> SimpleNamespace:
        return SimpleNamespace(topic=topic, payload=payload)

    # Non-V topics and metadata subtopics should be ignored without raising or flushing
    await consumer._handle_message(
        msg("telemetry/5YJ3E1EA1PF000001/connectivity", b'{"Status":"CONNECTED"}')
    )
    await consumer._handle_message(
        msg("telemetry/5YJ3E1EA1PF000001/alerts", b'[{"Name":"UI_a114"}]')
    )
    await consumer._handle_message(
        msg("telemetry/5YJ3E1EA1PF000001/v/CreatedAt", b'"2026-11-18T03:13:16Z"')
    )
    await consumer._handle_message(msg("telemetry/5YJ3E1EA1PF000001/v/VehicleSpeed", b"<invalid>"))
    assert engine.process_point.call_count == 0

    # Stream separate per-field payloads cleanly coalesced into a single VehicleTelemetryPoint
    await consumer._handle_message(msg("telemetry/5YJ3E1EA1PF000001/v/Soc", b"25.43"))
    await consumer._handle_message(msg("telemetry/5YJ3E1EA1PF000001/v/Odometer", b"100.0"))
    await consumer._handle_message(msg("telemetry/5YJ3E1EA1PF000001/v/RatedRange", b"50.0"))
    await consumer._handle_message(msg("telemetry/5YJ3E1EA1PF000001/v/Gear", b"ShiftStateP"))
    await consumer._handle_message(
        msg(
            "telemetry/5YJ3E1EA1PF000001/v/Location",
            b'{"latitude": 39.7817, "longitude": -89.6501}',
        )
    )

    import asyncio

    await asyncio.sleep(0.1)
    assert engine.process_point.call_count == 1
    point = engine.process_point.call_args.args[0]
    assert point.vin == "5YJ3E1EA1PF000001"
    assert point.battery_level == 25
    assert point.gear == "P"
    assert point.latitude == Decimal("39.7817")
    assert point.longitude == Decimal("-89.6501")
    assert point.odometer == pytest.approx(160.9344, rel=1e-4)
    assert float(point.rated_battery_range_km) == pytest.approx(80.4672, rel=1e-4)

    # Subsequent scalar-only frame must not re-send popped Location
    await consumer._handle_message(msg("telemetry/5YJ3E1EA1PF000001/v/Soc", b"26.0"))
    await asyncio.sleep(0.1)
    assert engine.process_point.call_count == 2
    point2 = engine.process_point.call_args.args[0]
    assert point2.battery_level == 26
    assert point2.latitude is None
    assert point2.longitude is None


@pytest.mark.asyncio
async def test_state_engine_updates_geofence_on_location_point():
    from fleetmate.geofences.detector import GeofenceRecord

    repo = AsyncMock()
    repo.insert_position.return_value = 102
    repo.find_geofence.return_value = GeofenceRecord(
        id=1, name="Home", latitude=Decimal("39.7817"), longitude=Decimal("-89.6501"), radius=50
    )
    geocoder = AsyncMock()
    publisher = StateMQTTPublisher(car_id=1, prefix="fleetmate", enabled=True)
    client = AsyncMock()
    publisher.set_client(client)

    engine = StateMachineEngine(repo=repo, car_id=1, geocoder=geocoder, publisher=publisher)
    point = VehicleTelemetryPoint.from_fleet_telemetry_json(
        vin="5YJ3E1EA1PF000001",
        raw_data={
            "Location": {"latitude": 39.7817, "longitude": -89.6501},
            "Locked": True,
            "SentryMode": "SentryModeStateArmed",
            "FdWindow": "WindowStateClosed",
            "HvacPower": "HvacPowerStateOff",
            "ClimateKeeperMode": "ClimateKeeperModeStateOff",
        },
    )
    await engine.process_point(point)

    published = {call.args[0]: call.args[1] for call in client.publish.call_args_list}
    assert published["fleetmate/cars/1/geofence"] == "Home"
    assert published["fleetmate/cars/1/locked"] == "true"
    assert published["fleetmate/cars/1/sentry_mode"] == "true"
    assert published["fleetmate/cars/1/driver_front_window_open"] == "false"
    assert published["fleetmate/cars/1/is_climate_on"] == "false"
    assert published["fleetmate/cars/1/climate_keeper_mode"] == "off"
