from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class VehicleTelemetryPoint(BaseModel):
    """
    Standardized in-memory vehicle telemetry record decoded from Fleet Telemetry.
    Maps directly to the FleetMate PostgreSQL schema: public.positions & public.drives.
    """

    vin: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    speed: int | None = None  # Stored in km/h in PostgreSQL
    power: int | None = None  # kW
    odometer: float | None = None  # km
    ideal_battery_range_km: Decimal | None = None
    rated_battery_range_km: Decimal | None = None
    est_battery_range_km: Decimal | None = None
    battery_level: int | None = None
    usable_battery_level: int | None = None
    outside_temp: Decimal | None = None
    inside_temp: Decimal | None = None
    elevation: int | None = None
    gear: str | None = None  # 'P', 'D', 'R', 'N'
    charge_state: str | None = None
    charger_voltage: int | None = None
    charger_actual_current: int | None = None
    charger_power: int | None = None  # kW
    charger_phases: int | None = None
    charger_pilot_current: int | None = None
    charge_energy_added: Decimal | None = None  # kWh
    fast_charger_present: bool | None = None
    fast_charger_brand: str | None = None
    fast_charger_type: str | None = None
    conn_charge_cable: str | None = None
    battery_heater_on: bool | None = None
    tpms_pressure_fl: Decimal | None = None
    tpms_pressure_fr: Decimal | None = None
    tpms_pressure_rl: Decimal | None = None
    tpms_pressure_rr: Decimal | None = None
    is_climate_on: bool | None = None

    @classmethod
    def from_fleet_telemetry_json(
        cls, vin: str, raw_data: dict[str, Any]
    ) -> "VehicleTelemetryPoint":
        """
        Parses JSON decoded by tesla/fleet-telemetry MQTT datastore.
        Handles both raw protobuf-mapped keys and flattened field names.
        """
        # Telemetry may arrive as key-value pairs or record payload
        payload = raw_data.get("data", raw_data)

        # Helper for numeric extraction
        def get_dec(val: Any) -> Decimal | None:
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except Exception:
                return None

        # Helper for int extraction
        def get_int(val: Any) -> int | None:
            if val is None:
                return None
            try:
                return int(round(float(val)))
            except Exception:
                return None

        # Helper for float extraction
        def get_float(val: Any) -> float | None:
            if val is None:
                return None
            try:
                return float(val)
            except Exception:
                return None

        # Coordinates may be nested in Location or flat
        loc = payload.get("Location", {})
        lat = (
            loc.get("latitude")
            if isinstance(loc, dict)
            else payload.get("latitude", payload.get("lat"))
        )
        lon = (
            loc.get("longitude")
            if isinstance(loc, dict)
            else payload.get("longitude", payload.get("lon"))
        )

        return cls(
            vin=vin,
            latitude=get_dec(lat),
            longitude=get_dec(lon),
            speed=get_int(payload.get("VehicleSpeed", payload.get("speed"))),
            power=get_int(payload.get("Power", payload.get("power"))),
            odometer=get_float(payload.get("Odometer", payload.get("odometer"))),
            ideal_battery_range_km=get_dec(
                payload.get("IdealBatteryRange", payload.get("ideal_battery_range_km"))
            ),
            rated_battery_range_km=get_dec(
                payload.get(
                    "RatedRange",
                    payload.get("RatedBatteryRange", payload.get("rated_battery_range_km")),
                )
            ),
            est_battery_range_km=get_dec(
                payload.get("EstBatteryRange", payload.get("est_battery_range_km"))
            ),
            battery_level=get_int(
                payload.get("Soc", payload.get("BatteryLevel", payload.get("battery_level")))
            ),
            usable_battery_level=get_int(
                payload.get("UsableBatteryLevel", payload.get("usable_battery_level"))
            ),
            outside_temp=get_dec(payload.get("OutsideTemp", payload.get("outside_temp"))),
            inside_temp=get_dec(payload.get("InsideTemp", payload.get("inside_temp"))),
            gear=payload.get("Gear", payload.get("gear")),
            charge_state=payload.get(
                "DetailedChargeState",
                payload.get("ChargeState", payload.get("charge_state")),
            ),
            charger_voltage=get_int(payload.get("ChargerVoltage", payload.get("charger_voltage"))),
            charger_actual_current=get_int(
                payload.get(
                    "ChargeAmps",
                    payload.get("ChargerActualCurrent", payload.get("charger_actual_current")),
                )
            ),
            charger_power=get_int(
                payload.get(
                    "ChargerPower",
                    payload.get(
                        "ACChargingPower",
                        payload.get("DCChargingPower", payload.get("charger_power")),
                    ),
                )
            ),
            charger_phases=get_int(payload.get("ChargerPhases", payload.get("charger_phases"))),
            charger_pilot_current=get_int(
                payload.get(
                    "ChargeCurrentRequest",
                    payload.get("ChargerPilotCurrent", payload.get("charger_pilot_current")),
                )
            ),
            charge_energy_added=get_dec(
                payload.get(
                    "ChargeEnergyAdded",
                    payload.get(
                        "ACChargingEnergyIn",
                        payload.get("DCChargingEnergyIn", payload.get("charge_energy_added")),
                    ),
                )
            ),
            fast_charger_present=payload.get(
                "FastChargerPresent", payload.get("fast_charger_present")
            ),
            fast_charger_brand=payload.get("FastChargerBrand", payload.get("fast_charger_brand")),
            fast_charger_type=payload.get("FastChargerType", payload.get("fast_charger_type")),
            conn_charge_cable=payload.get("ConnChargeCable", payload.get("conn_charge_cable")),
            battery_heater_on=payload.get("BatteryHeaterOn", payload.get("battery_heater_on")),
            tpms_pressure_fl=get_dec(
                payload.get(
                    "TpmsPressureFl",
                    payload.get("TirePressureFrontLeft", payload.get("tpms_pressure_fl")),
                )
            ),
            tpms_pressure_fr=get_dec(
                payload.get(
                    "TpmsPressureFr",
                    payload.get("TirePressureFrontRight", payload.get("tpms_pressure_fr")),
                )
            ),
            tpms_pressure_rl=get_dec(
                payload.get(
                    "TpmsPressureRl",
                    payload.get("TirePressureRearLeft", payload.get("tpms_pressure_rl")),
                )
            ),
            tpms_pressure_rr=get_dec(
                payload.get(
                    "TpmsPressureRr",
                    payload.get("TirePressureRearRight", payload.get("tpms_pressure_rr")),
                )
            ),
            is_climate_on=payload.get("IsClimateOn", payload.get("is_climate_on")),
        )
