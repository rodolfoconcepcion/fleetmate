from decimal import Decimal

from fleetmate.telemetry.models import VehicleTelemetryPoint


def test_vehicle_telemetry_point_parsing():
    raw_payload = {
        "Location": {
            "latitude": 26.0682,
            "longitude": -80.2451,
        },
        "VehicleSpeed": 65,
        "Power": 24,
        "Odometer": 15420.5,
        "BatteryLevel": 78,
        "Gear": "D",
        "OutsideTemp": 82.5,
        "InsideTemp": 72.0,
        "TirePressureFrontLeft": 2.9,
        "TirePressureFrontRight": 2.9,
        "TirePressureRearLeft": 2.9,
        "TirePressureRearRight": 2.9,
        "RatedBatteryRange": 412.5,
        "IsClimateOn": True,
    }

    point = VehicleTelemetryPoint.from_fleet_telemetry_json(
        vin="5YJ3E1EBXRF822141",
        raw_data=raw_payload,
    )

    assert point.vin == "5YJ3E1EBXRF822141"
    assert point.latitude == Decimal("26.0682")
    assert point.longitude == Decimal("-80.2451")
    assert point.speed == 65
    assert point.power == 24
    assert point.gear == "D"
    assert point.battery_level == 78
    assert point.outside_temp == Decimal("82.5")
    assert point.inside_temp == Decimal("72.0")
    assert point.tpms_pressure_fl == Decimal("2.9")
    assert point.tpms_pressure_fr == Decimal("2.9")
    assert point.tpms_pressure_rl == Decimal("2.9")
    assert point.tpms_pressure_rr == Decimal("2.9")
    assert point.rated_battery_range_km == Decimal("412.5")
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
