from decimal import Decimal

from fleetmate.telemetry.models import VehicleTelemetryPoint


def test_vehicle_telemetry_point_parsing():
    raw_payload = {
        "Location": {
            "latitude": 40.7128,
            "longitude": -74.0060,
        },
        "VehicleSpeed": 65,
        "Power": 24,
        "Odometer": 15420.5,
        "Soc": 78,
        "RatedRange": 412.5,
        "ChargeAmps": 32,
        "Gear": "D",
        "OutsideTemp": 22.5,
        "InsideTemp": 21.0,
        "TpmsPressureFl": 2.8,
        "TpmsPressureFr": 2.9,
        "TpmsPressureRl": 3.0,
        "TpmsPressureRr": 3.1,
        "IsClimateOn": True,
    }

    point = VehicleTelemetryPoint.from_fleet_telemetry_json(
        vin="5YJ3E1EA1PF000001",
        raw_data=raw_payload,
    )

    assert point.vin == "5YJ3E1EA1PF000001"
    assert point.latitude == Decimal("40.7128")
    assert point.longitude == Decimal("-74.006")
    assert point.speed == 65
    assert point.power == 24
    assert point.gear == "D"
    assert point.battery_level == 78
    assert point.outside_temp == Decimal("22.5")
    assert point.inside_temp == Decimal("21.0")
    assert point.tpms_pressure_fl == Decimal("2.8")
    assert point.tpms_pressure_fr == Decimal("2.9")
    assert point.tpms_pressure_rl == Decimal("3.0")
    assert point.tpms_pressure_rr == Decimal("3.1")
    assert point.rated_battery_range_km == Decimal("412.5")
    assert point.charger_actual_current == 32
    assert point.is_climate_on is True


def test_vehicle_telemetry_handles_missing_fields():
    point = VehicleTelemetryPoint.from_fleet_telemetry_json(
        vin="TESTVIN1234567890",
        raw_data={},
    )
    assert point.vin == "TESTVIN1234567890"
    assert point.latitude is None
    assert point.longitude is None
    assert point.speed is None
    assert point.tpms_pressure_fl is None
    assert point.is_climate_on is None
