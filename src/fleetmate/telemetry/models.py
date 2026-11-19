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
    tpms_soft_warning_fl: bool | None = None
    tpms_soft_warning_fr: bool | None = None
    tpms_soft_warning_rl: bool | None = None
    tpms_soft_warning_rr: bool | None = None
    is_climate_on: bool | None = None
    is_preconditioning: bool | None = None
    climate_keeper_mode: str | None = None
    charge_limit_soc: int | None = None
    charge_port_door_open: bool | None = None
    time_to_full_charge: float | None = None
    charge_current_request: int | None = None
    plugged_in: bool | None = None
    locked: bool | None = None
    doors_open: bool | None = None
    driver_front_door_open: bool | None = None
    passenger_front_door_open: bool | None = None
    driver_rear_door_open: bool | None = None
    passenger_rear_door_open: bool | None = None
    windows_open: bool | None = None
    driver_front_window_open: bool | None = None
    passenger_front_window_open: bool | None = None
    driver_rear_window_open: bool | None = None
    passenger_rear_window_open: bool | None = None
    trunk_open: bool | None = None
    frunk_open: bool | None = None
    sentry_mode: bool | None = None
    heading: int | None = None
    version: str | None = None
    is_user_present: bool | None = None

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

        # Helper for string extraction
        def get_str(val: Any) -> str | None:
            if not isinstance(val, str):
                return None
            clean = val.strip()
            if clean in {"", "<invalid>", "ShiftStateInvalid", "ShiftStateSNA"}:
                return None
            return clean

        def normalize_gear(val: Any) -> str | None:
            clean = get_str(val)
            if clean is None:
                return None
            gear_map = {
                "ShiftStateP": "P",
                "ShiftStateD": "D",
                "ShiftStateR": "R",
                "ShiftStateN": "N",
            }
            return gear_map.get(clean, clean)

        def normalize_climate_keeper(val: Any) -> str | None:
            clean = get_str(val)
            if clean is None or clean == "ClimateKeeperModeStateUnknown":
                return None
            keeper_map = {
                "ClimateKeeperModeStateOff": "off",
                "ClimateKeeperModeStateOn": "on",
                "ClimateKeeperModeStateDog": "dog",
                "ClimateKeeperModeStateParty": "party",
            }
            return keeper_map.get(clean, clean)

        # Helper for bool extraction
        def get_bool(val: Any) -> bool | None:
            if val is None:
                return None
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                low = val.strip().lower()
                if low in {
                    "true",
                    "1",
                    "yes",
                    "on",
                    "open",
                    "opened",
                    "engaged",
                    "latched",
                    "sentrymodestateidle",
                    "sentrymodestatearmed",
                    "sentrymodestateaware",
                    "sentrymodestatepanic",
                    "sentrymodestatequiet",
                    "windowstatepartiallyopen",
                    "windowstateopened",
                    "hvacpowerstateon",
                    "hvacpowerstateprecondition",
                    "hvacpowerstateoverheatprotect",
                    "chargeportlatchengaged",
                }:
                    return True
                if low in {
                    "false",
                    "0",
                    "no",
                    "off",
                    "closed",
                    "disengaged",
                    "unlatched",
                    "sentrymodestateoff",
                    "windowstateclosed",
                    "hvacpowerstateoff",
                    "chargeportlatchdisengaged",
                    "chargeportlatchblocking",
                }:
                    return False
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

        door_state = payload.get("DoorState") if isinstance(payload.get("DoorState"), dict) else {}
        df_door = get_bool(
            door_state.get("DriverFront", payload.get("driver_front_door_open"))
        )
        pf_door = get_bool(
            door_state.get("PassengerFront", payload.get("passenger_front_door_open"))
        )
        dr_door = get_bool(
            door_state.get("DriverRear", payload.get("driver_rear_door_open"))
        )
        pr_door = get_bool(
            door_state.get("PassengerRear", payload.get("passenger_rear_door_open"))
        )
        trunk_open = get_bool(
            door_state.get("TrunkRear", payload.get("TrunkOpen", payload.get("trunk_open")))
        )
        frunk_open = get_bool(
            door_state.get("TrunkFront", payload.get("FrunkOpen", payload.get("frunk_open")))
        )
        door_flags = [d for d in (df_door, pf_door, dr_door, pr_door) if d is not None]
        doors_open = get_bool(payload.get("DoorsOpen", payload.get("doors_open")))
        if doors_open is None and door_flags:
            doors_open = any(door_flags)

        df_win = get_bool(payload.get("FdWindow", payload.get("driver_front_window_open")))
        pf_win = get_bool(payload.get("FpWindow", payload.get("passenger_front_window_open")))
        dr_win = get_bool(payload.get("RdWindow", payload.get("driver_rear_window_open")))
        pr_win = get_bool(payload.get("RpWindow", payload.get("passenger_rear_window_open")))
        win_flags = [w for w in (df_win, pf_win, dr_win, pr_win) if w is not None]
        windows_open = get_bool(payload.get("WindowsOpen", payload.get("windows_open")))
        if windows_open is None and win_flags:
            windows_open = any(win_flags)

        power_val = get_int(payload.get("Power", payload.get("power")))
        if power_val is None:
            pack_v = get_float(payload.get("PackVoltage"))
            pack_a = get_float(payload.get("PackCurrent"))
            if pack_v is not None and pack_a is not None:
                power_val = int(round((pack_v * pack_a) / 1000.0))

        return cls(
            vin=vin,
            latitude=get_dec(lat),
            longitude=get_dec(lon),
            speed=get_int(payload.get("VehicleSpeed", payload.get("speed"))),
            power=power_val,
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
            gear=normalize_gear(payload.get("Gear", payload.get("gear"))),
            charge_state=get_str(
                payload.get(
                    "DetailedChargeState",
                    payload.get("ChargeState", payload.get("charge_state")),
                )
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
            fast_charger_present=get_bool(
                payload.get("FastChargerPresent", payload.get("fast_charger_present"))
            ),
            fast_charger_brand=get_str(
                payload.get("FastChargerBrand", payload.get("fast_charger_brand"))
            ),
            fast_charger_type=get_str(
                payload.get("FastChargerType", payload.get("fast_charger_type"))
            ),
            conn_charge_cable=get_str(
                payload.get("ConnChargeCable", payload.get("conn_charge_cable"))
            ),
            battery_heater_on=get_bool(
                payload.get("BatteryHeaterOn", payload.get("battery_heater_on"))
            ),
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
            tpms_soft_warning_fl=get_bool(
                payload.get("TpmsHardWarnings", payload.get("tpms_soft_warning_fl"))
            ),
            tpms_soft_warning_fr=get_bool(payload.get("tpms_soft_warning_fr")),
            tpms_soft_warning_rl=get_bool(payload.get("tpms_soft_warning_rl")),
            tpms_soft_warning_rr=get_bool(payload.get("tpms_soft_warning_rr")),
            is_climate_on=get_bool(
                payload.get("IsClimateOn", payload.get("HvacPower", payload.get("is_climate_on")))
            ),
            is_preconditioning=get_bool(
                payload.get("PreconditioningEnabled", payload.get("is_preconditioning"))
            ),
            climate_keeper_mode=normalize_climate_keeper(
                payload.get("ClimateKeeperMode", payload.get("climate_keeper_mode"))
            ),
            charge_limit_soc=get_int(
                payload.get("ChargeLimitSoc", payload.get("charge_limit_soc"))
            ),
            charge_port_door_open=get_bool(
                payload.get("ChargePortDoorOpen", payload.get("charge_port_door_open"))
            ),
            time_to_full_charge=get_float(
                payload.get("TimeToFullCharge", payload.get("time_to_full_charge"))
            ),
            charge_current_request=get_int(
                payload.get("ChargeCurrentRequest", payload.get("charge_current_request"))
            ),
            plugged_in=get_bool(payload.get("ChargePortLatch", payload.get("plugged_in"))),
            locked=get_bool(payload.get("Locked", payload.get("locked"))),
            doors_open=doors_open,
            driver_front_door_open=df_door,
            passenger_front_door_open=pf_door,
            driver_rear_door_open=dr_door,
            passenger_rear_door_open=pr_door,
            windows_open=windows_open,
            driver_front_window_open=df_win,
            passenger_front_window_open=pf_win,
            driver_rear_window_open=dr_win,
            passenger_rear_window_open=pr_win,
            trunk_open=trunk_open,
            frunk_open=frunk_open,
            sentry_mode=get_bool(payload.get("SentryMode", payload.get("sentry_mode"))),
            heading=get_int(payload.get("GpsHeading", payload.get("heading"))),
            elevation=get_int(payload.get("Elevation", payload.get("elevation"))),
            version=get_str(payload.get("Version", payload.get("version"))),
            is_user_present=get_bool(
                payload.get("DriverSeatOccupied", payload.get("is_user_present"))
            ),
        )
