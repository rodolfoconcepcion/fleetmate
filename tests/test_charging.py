from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from fleetmate.geocoding.nominatim import ResolvedAddress
from fleetmate.state.engine import StateMachineEngine, VehicleState
from fleetmate.telemetry.models import VehicleTelemetryPoint


@pytest.mark.asyncio
async def test_charging_session_lifecycle_and_kwh_integration():
    repo = AsyncMock()
    repo.insert_position.return_value = 501
    repo.start_charging_process.return_value = 9001
    repo.insert_charge.return_value = 1001
    repo.upsert_address.return_value = 301
    repo.find_geofence.return_value = None

    geocoder = AsyncMock()
    geocoder.reverse_geocode.return_value = ResolvedAddress(
        osm_id=123456,
        osm_type="way",
        display_name="123 Main St, Springfield, IL 62701, USA",
        latitude=Decimal("39.7817"),
        longitude=Decimal("-89.6501"),
        name="Home Charger",
        house_number="123",
        road="Main St",
        neighbourhood="Downtown",
        city="Springfield",
        county="Sangamon County",
        postcode="62701",
        state="Illinois",
        state_district=None,
        country="United States",
        raw={},
    )

    engine = StateMachineEngine(repo=repo, car_id=1, geocoder=geocoder)
    t0 = datetime(2026, 11, 8, 12, 0, 0, tzinfo=UTC)

    # 1. Start charging at 240V / 32A (~8 kW) with generic coordinates
    p1 = VehicleTelemetryPoint.from_fleet_telemetry_json(
        "5YJ3E1EA1PF000001",
        {
            "Location": {"latitude": 39.7817, "longitude": -89.6501},
            "ChargeState": "Charging",
            "ChargerVoltage": 240,
            "ChargeAmps": 32,
            "ChargerPhases": 1,
            "Soc": 50,
            "RatedRange": 240.0,
            "OutsideTemp": 22.0,
        },
    ).model_copy(update={"timestamp": t0})

    await engine.process_point(p1)

    assert engine.current_state == VehicleState.CHARGING
    assert engine.current_charging_process_id == 9001
    repo.start_charging_process.assert_awaited_once()
    repo.insert_charge.assert_awaited_once()

    # Wait for background address resolution
    for task in list(engine._background_tasks):
        await task
    repo.update_charging_process_address.assert_awaited_once_with(
        charging_process_id=9001,
        address_id=301,
        geofence_id=None,
    )

    # 2. Sample 30 minutes later at 8 kW -> ~4.00 kWh integrated
    t1 = t0 + timedelta(minutes=30)
    p2 = VehicleTelemetryPoint.from_fleet_telemetry_json(
        "5YJ3E1EA1PF000001",
        {
            "ChargeState": "Charging",
            "ChargerVoltage": 240,
            "ChargeAmps": 32,
            "ChargerPhases": 1,
            "Soc": 56,
            "RatedRange": 268.0,
        },
    ).model_copy(update={"timestamp": t1})

    await engine.process_point(p2)
    assert engine.charge_energy_added_kwh == Decimal("4.00")
    assert repo.insert_charge.await_count == 2

    # 3. Disconnect / Complete after 60 minutes with explicit ChargeEnergyAdded
    t2 = t0 + timedelta(minutes=60)
    p3 = VehicleTelemetryPoint.from_fleet_telemetry_json(
        "5YJ3E1EA1PF000001",
        {
            "ChargeState": "Complete",
            "ChargerVoltage": 0,
            "ChargeAmps": 0,
            "ChargeEnergyAdded": 8.15,
            "Soc": 62,
            "RatedRange": 295.0,
        },
    ).model_copy(update={"timestamp": t2})

    await engine.process_point(p3)

    assert engine.current_state == VehicleState.ONLINE
    assert engine.current_charging_process_id is None
    repo.end_charging_process.assert_awaited_once_with(
        charging_process_id=9001,
        end_time=t2,
        end_battery_level=62,
        end_ideal_range_km=None,
        end_rated_range_km=Decimal("295.0"),
        charge_energy_added=Decimal("8.15"),
        geofence_id=None,
        cost=None,
    )
