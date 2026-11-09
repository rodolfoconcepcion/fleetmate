from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from fleetmate.geofences.detector import (
    GeofenceRecord,
    calculate_charging_cost,
    find_matching_geofence,
    haversine_distance_meters,
)
from fleetmate.state.engine import StateMachineEngine
from fleetmate.telemetry.models import VehicleTelemetryPoint


def test_haversine_and_geofence_matching():
    home_gf = GeofenceRecord(
        id=1,
        name="Home Garage",
        latitude=Decimal("39.781700"),
        longitude=Decimal("-89.650100"),
        radius=50,
        cost_per_unit=Decimal("0.1400"),
        session_fee=Decimal("0.00"),
        billing_type="per_kwh",
    )
    office_gf = GeofenceRecord(
        id=2,
        name="Downtown Office",
        latitude=Decimal("39.800000"),
        longitude=Decimal("-89.700000"),
        radius=100,
        cost_per_unit=Decimal("0.2500"),
        session_fee=Decimal("1.50"),
        billing_type="per_kwh",
    )

    # Exact center -> 0 meters
    d0 = haversine_distance_meters(
        Decimal("39.781700"),
        Decimal("-89.650100"),
        home_gf.latitude,
        home_gf.longitude,
    )
    assert d0 < 0.01

    # ~15 meters away -> inside Home Garage (50m radius)
    matched = find_matching_geofence(
        Decimal("39.781800"),
        Decimal("-89.650100"),
        [home_gf, office_gf],
    )
    assert matched is not None
    assert matched.id == 1
    assert matched.name == "Home Garage"

    # Far outside both geofences -> None
    unmatched = find_matching_geofence(
        Decimal("40.000000"),
        Decimal("-90.000000"),
        [home_gf, office_gf],
    )
    assert unmatched is None


def test_electricity_cost_calculator():
    per_kwh_gf = GeofenceRecord(
        id=1,
        name="Home Garage",
        latitude=Decimal("39.781700"),
        longitude=Decimal("-89.650100"),
        radius=50,
        cost_per_unit=Decimal("0.1450"),
        session_fee=Decimal("0.50"),
        billing_type="per_kwh",
    )
    per_min_gf = GeofenceRecord(
        id=2,
        name="Public Station",
        latitude=Decimal("39.800000"),
        longitude=Decimal("-89.700000"),
        radius=50,
        cost_per_unit=Decimal("0.2000"),
        session_fee=Decimal("1.00"),
        billing_type="per_minute",
    )

    # 20 kWh * $0.1450 + $0.50 = $3.40
    cost_kwh = calculate_charging_cost(
        geofence=per_kwh_gf,
        charge_energy_added_kwh=Decimal("20.00"),
        duration_min=120,
    )
    assert cost_kwh == Decimal("3.40")

    # 45 min * $0.20 + $1.00 = $10.00
    cost_min = calculate_charging_cost(
        geofence=per_min_gf,
        charge_energy_added_kwh=Decimal("15.00"),
        duration_min=45,
    )
    assert cost_min == Decimal("10.00")

    assert calculate_charging_cost(None, Decimal("20.00")) is None


@pytest.mark.asyncio
async def test_charging_session_with_geofence_tariff():
    home_gf = GeofenceRecord(
        id=7,
        name="Home Garage",
        latitude=Decimal("39.781700"),
        longitude=Decimal("-89.650100"),
        radius=50,
        cost_per_unit=Decimal("0.1500"),
        session_fee=Decimal("0.00"),
        billing_type="per_kwh",
    )

    repo = AsyncMock()
    repo.insert_position.return_value = 701
    repo.start_charging_process.return_value = 9500
    repo.insert_charge.return_value = 2001
    repo.upsert_address.return_value = 401
    repo.find_geofence.return_value = home_gf

    geocoder = AsyncMock()
    geocoder.reverse_geocode.return_value = None

    engine = StateMachineEngine(repo=repo, car_id=1, geocoder=geocoder)
    t0 = datetime(2026, 11, 9, 8, 0, 0, tzinfo=UTC)

    p_start = VehicleTelemetryPoint.from_fleet_telemetry_json(
        "5YJ3E1EA1PF000001",
        {
            "Location": {"latitude": 39.7817, "longitude": -89.6501},
            "ChargeState": "Charging",
            "ChargerVoltage": 240,
            "ChargeAmps": 40,
            "Soc": 40,
        },
    ).model_copy(update={"timestamp": t0})

    await engine.process_point(p_start)
    for task in list(engine._background_tasks):
        await task

    repo.update_charging_process_address.assert_awaited_once_with(
        charging_process_id=9500,
        address_id=None,
        geofence_id=7,
    )

    t_end = t0 + timedelta(hours=2)
    p_end = VehicleTelemetryPoint.from_fleet_telemetry_json(
        "5YJ3E1EA1PF000001",
        {
            "ChargeState": "Complete",
            "ChargeEnergyAdded": 20.00,
            "Soc": 70,
        },
    ).model_copy(update={"timestamp": t_end})

    await engine.process_point(p_end)

    # 20.00 kWh * $0.1500 = $3.00
    repo.end_charging_process.assert_awaited_once_with(
        charging_process_id=9500,
        end_time=t_end,
        end_battery_level=70,
        end_ideal_range_km=None,
        end_rated_range_km=None,
        charge_energy_added=Decimal("20.0"),
        geofence_id=7,
        cost=Decimal("3.00"),
    )
