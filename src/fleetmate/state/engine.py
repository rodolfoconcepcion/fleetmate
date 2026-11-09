import asyncio
import logging
from collections.abc import Coroutine
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from fleetmate.config.settings import settings
from fleetmate.geocoding.nominatim import NominatimGeocoder
from fleetmate.geofences.detector import GeofenceRecord, calculate_charging_cost
from fleetmate.metrics.prometheus import CHARGES_DETECTED, DRIVES_DETECTED, GEOFENCE_MATCHES
from fleetmate.storage.postgres import FleetMateRepository
from fleetmate.telemetry.models import VehicleTelemetryPoint

logger = logging.getLogger(__name__)

ACTIVE_CHARGE_STATES = frozenset(
    {
        "Charging",
        "Starting",
        "DetailedChargeStateCharging",
        "DetailedChargeStateStarting",
    }
)

TERMINAL_CHARGE_STATES = frozenset(
    {
        "Complete",
        "Stopped",
        "Disconnected",
        "NoPower",
        "DetailedChargeStateComplete",
        "DetailedChargeStateStopped",
        "DetailedChargeStateDisconnected",
        "DetailedChargeStateNoPower",
    }
)


class VehicleState(StrEnum):
    ASLEEP = "asleep"
    ONLINE = "online"
    DRIVING = "driving"
    CHARGING = "charging"


class StateMachineEngine:
    """
    Real-time State Machine Engine.
    Detects transitions between Driving, Charging, Online, and Sleeping
    based on live incoming Fleet Telemetry events, seamlessly managing
    trip boundaries (drives & charges) and background reverse geocoding
    with zero API polling.
    """

    def __init__(
        self,
        repo: FleetMateRepository,
        car_id: int = settings.car_id,
        geocoder: NominatimGeocoder | None = None,
    ) -> None:
        self.repo = repo
        self.car_id = car_id
        self.geocoder = geocoder or NominatimGeocoder()
        self.current_state: VehicleState = VehicleState.ONLINE
        self.current_drive_id: int | None = None
        self.drive_start_time: datetime | None = None
        self.drive_start_odometer: float | None = None
        self.drive_start_geocoded: bool = False
        self.current_charging_process_id: int | None = None
        self.current_charging_geofence: GeofenceRecord | None = None
        self.charge_start_time: datetime | None = None
        self.charge_energy_added_kwh: Decimal = Decimal("0.00")
        self.last_charge_sample_time: datetime | None = None
        self.last_charger_power_kw: int = 0
        self.last_charger_voltage: int | None = None
        self.last_charger_current: int | None = None
        self.last_battery_level: int | None = None
        self.last_ideal_range_km: Decimal | None = None
        self.last_rated_range_km: Decimal | None = None
        self.last_point: VehicleTelemetryPoint | None = None
        self.last_coords: tuple[Decimal, Decimal] | None = None
        self.last_position_id: int | None = None
        self.last_motion_time: datetime | None = None
        self._background_tasks: set[asyncio.Task[None]] = set()

    def _spawn_background(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _resolve_start_address(
        self,
        drive_id: int,
        latitude: Decimal,
        longitude: Decimal,
        position_id: int | None,
    ) -> None:
        matched_gf = await self.repo.find_geofence(latitude, longitude)
        geofence_id = matched_gf.id if matched_gf else None
        if matched_gf:
            GEOFENCE_MATCHES.labels(context="drive_start").inc()

        resolved = await self.geocoder.reverse_geocode(latitude, longitude)
        address_id = await self.repo.upsert_address(resolved) if resolved else None
        await self.repo.update_drive_start_location(
            drive_id=drive_id,
            address_id=address_id,
            position_id=position_id,
            geofence_id=geofence_id,
        )

    async def _finalize_drive_with_geocoding(
        self,
        drive_id: int,
        end_time: datetime,
        end_odometer: float | None,
        end_ideal_range_km: Decimal | None,
        end_rated_range_km: Decimal | None,
        start_odometer: float | None,
        coords: tuple[Decimal, Decimal] | None,
        end_position_id: int | None,
    ) -> None:
        end_address_id: int | None = None
        end_geofence_id: int | None = None
        if coords is not None:
            matched_gf = await self.repo.find_geofence(coords[0], coords[1])
            if matched_gf:
                end_geofence_id = matched_gf.id
                GEOFENCE_MATCHES.labels(context="drive_end").inc()

            resolved = await self.geocoder.reverse_geocode(coords[0], coords[1])
            if resolved:
                end_address_id = await self.repo.upsert_address(resolved)

        await self.repo.end_drive(
            drive_id=drive_id,
            end_time=end_time,
            end_odometer=end_odometer,
            end_ideal_range_km=end_ideal_range_km,
            end_rated_range_km=end_rated_range_km,
            start_odometer=start_odometer,
            end_address_id=end_address_id,
            end_position_id=end_position_id,
            end_geofence_id=end_geofence_id,
        )

    async def _resolve_charging_address(
        self,
        charging_process_id: int,
        latitude: Decimal,
        longitude: Decimal,
    ) -> None:
        matched_gf = await self.repo.find_geofence(latitude, longitude)
        geofence_id = matched_gf.id if matched_gf else None
        if matched_gf:
            self.current_charging_geofence = matched_gf
            GEOFENCE_MATCHES.labels(context="charging").inc()

        resolved = await self.geocoder.reverse_geocode(latitude, longitude)
        address_id = await self.repo.upsert_address(resolved) if resolved else None
        if address_id is not None or geofence_id is not None:
            await self.repo.update_charging_process_address(
                charging_process_id=charging_process_id,
                address_id=address_id,
                geofence_id=geofence_id,
            )

    def _compute_charger_power_kw(self, point: VehicleTelemetryPoint) -> int:
        if point.charger_power is not None and point.charger_power > 0:
            return point.charger_power
        voltage = point.charger_voltage or self.last_charger_voltage
        current = point.charger_actual_current or self.last_charger_current
        phases = point.charger_phases if (point.charger_phases and point.charger_phases > 0) else 1
        if voltage and current and voltage > 0 and current > 0:
            return max(1, int(round((voltage * current * phases) / 1000.0)))
        if point.power is not None and point.power < 0:
            return abs(point.power)
        return self.last_charger_power_kw

    def _is_charging_signal(self, point: VehicleTelemetryPoint) -> bool:
        if point.charge_state in ACTIVE_CHARGE_STATES:
            return True
        if point.charge_state in TERMINAL_CHARGE_STATES:
            return False
        return bool(
            self.current_state != VehicleState.DRIVING
            and point.charger_actual_current is not None
            and point.charger_actual_current > 0
            and point.charger_voltage is not None
            and point.charger_voltage > 10
        )

    def _is_charging_stopped_signal(self, point: VehicleTelemetryPoint, is_in_motion: bool) -> bool:
        if is_in_motion:
            return True
        if point.charge_state in TERMINAL_CHARGE_STATES:
            return True
        return bool(
            point.charge_state is None
            and point.charger_actual_current is not None
            and point.charger_actual_current == 0
            and (point.charger_power is None or point.charger_power == 0)
        )

    async def _close_active_charging_session(
        self, end_time: datetime, point: VehicleTelemetryPoint
    ) -> None:
        if self.current_charging_process_id is None:
            return
        cp_id = self.current_charging_process_id
        final_soc = (
            point.battery_level if point.battery_level is not None else self.last_battery_level
        )
        final_ideal = (
            point.ideal_battery_range_km
            if point.ideal_battery_range_km is not None
            else self.last_ideal_range_km
        )
        final_rated = (
            point.rated_battery_range_km
            if point.rated_battery_range_km is not None
            else self.last_rated_range_km
        )
        final_energy = (
            point.charge_energy_added
            if point.charge_energy_added is not None
            else self.charge_energy_added_kwh
        )
        duration_min = (
            max(0, int(round((end_time - self.charge_start_time).total_seconds() / 60.0)))
            if self.charge_start_time
            else 0
        )
        matched_gf = self.current_charging_geofence
        if matched_gf is None and self.last_coords is not None:
            matched_gf = await self.repo.find_geofence(self.last_coords[0], self.last_coords[1])

        calculated_cost = calculate_charging_cost(
            geofence=matched_gf,
            charge_energy_added_kwh=final_energy,
            duration_min=duration_min,
        )
        CHARGES_DETECTED.labels(event="end").inc()
        await self.repo.end_charging_process(
            charging_process_id=cp_id,
            end_time=end_time,
            end_battery_level=final_soc,
            end_ideal_range_km=final_ideal,
            end_rated_range_km=final_rated,
            charge_energy_added=final_energy,
            geofence_id=matched_gf.id if matched_gf else None,
            cost=calculated_cost,
        )
        self.current_charging_process_id = None
        self.current_charging_geofence = None
        self.charge_start_time = None
        self.charge_energy_added_kwh = Decimal("0.00")
        self.last_charge_sample_time = None
        self.last_charger_power_kw = 0
        self.last_charger_voltage = None
        self.last_charger_current = None

    async def process_point(self, point: VehicleTelemetryPoint) -> None:
        """
        Processes a single incoming telemetry point, updates state machine,
        and coordinates persistence into PostgreSQL.
        """
        now = point.timestamp
        if point.latitude is not None and point.longitude is not None:
            self.last_coords = (point.latitude, point.longitude)
        if point.battery_level is not None:
            self.last_battery_level = point.battery_level
        if point.ideal_battery_range_km is not None:
            self.last_ideal_range_km = point.ideal_battery_range_km
        if point.rated_battery_range_km is not None:
            self.last_rated_range_km = point.rated_battery_range_km
        if point.charger_voltage is not None and point.charger_voltage > 0:
            self.last_charger_voltage = point.charger_voltage
        if point.charger_actual_current is not None and point.charger_actual_current >= 0:
            self.last_charger_current = point.charger_actual_current

        # Determine motion & gear
        is_in_motion = (point.speed is not None and point.speed > 0) or (point.gear in ["D", "R"])

        # Close active charging session if vehicle starts driving
        if is_in_motion and self.current_state == VehicleState.CHARGING:
            logger.info("⚡ [CHARGE END DETECTED] Vehicle shifted into motion while charging.")
            await self._close_active_charging_session(now, point)
            self.current_state = VehicleState.ONLINE

        # 1. Drive Detection Transition
        if is_in_motion:
            self.last_motion_time = now
            if self.current_state != VehicleState.DRIVING:
                logger.info(
                    "🚗 [DRIVE START DETECTED] Vehicle in motion (Speed: %s, Gear: %s)",
                    point.speed,
                    point.gear,
                )
                self.current_state = VehicleState.DRIVING
                self.drive_start_time = now
                self.drive_start_odometer = point.odometer
                self.drive_start_geocoded = False
                self.current_drive_id = await self.repo.start_drive(
                    car_id=self.car_id,
                    start_time=now,
                    start_odometer=point.odometer,
                    start_ideal_range_km=point.ideal_battery_range_km,
                    start_rated_range_km=point.rated_battery_range_km,
                )
                DRIVES_DETECTED.labels(event="start").inc()
                logger.info("Created new drive #%s in database.", self.current_drive_id)

        # 2. Insert valid coordinate points before finalizing drive so position belongs to drive
        inserted_pos_id: int | None = None
        if point.latitude is not None and point.longitude is not None:
            inserted_pos_id = await self.repo.insert_position(
                point=point,
                car_id=self.car_id,
                drive_id=self.current_drive_id,
            )
            if inserted_pos_id is not None:
                self.last_position_id = inserted_pos_id

            # Trigger start-of-drive reverse geocoding on first valid coordinates of the drive
            if (
                self.current_state == VehicleState.DRIVING
                and self.current_drive_id is not None
                and not self.drive_start_geocoded
            ):
                self.drive_start_geocoded = True
                self._spawn_background(
                    self._resolve_start_address(
                        drive_id=self.current_drive_id,
                        latitude=point.latitude,
                        longitude=point.longitude,
                        position_id=inserted_pos_id,
                    )
                )

        # 3. Drive End Detection Transition (Parked or idle timeout)
        if not is_in_motion and self.current_state == VehicleState.DRIVING:
            idle_seconds = (
                (now - self.last_motion_time).total_seconds() if self.last_motion_time else 0
            )
            if point.gear == "P" or idle_seconds > settings.drive_idle_timeout_seconds:
                logger.info(
                    "🅿️ [DRIVE END DETECTED] Vehicle parked (Gear: %s, Idle: %0.1fs)",
                    point.gear,
                    idle_seconds,
                )
                if self.current_drive_id is not None:
                    drive_id_to_close = self.current_drive_id
                    start_odo = self.drive_start_odometer
                    coords_to_resolve = self.last_coords
                    end_pos_id = inserted_pos_id or self.last_position_id
                    DRIVES_DETECTED.labels(event="end").inc()
                    self._spawn_background(
                        self._finalize_drive_with_geocoding(
                            drive_id=drive_id_to_close,
                            end_time=now,
                            end_odometer=point.odometer,
                            end_ideal_range_km=point.ideal_battery_range_km,
                            end_rated_range_km=point.rated_battery_range_km,
                            start_odometer=start_odo,
                            coords=coords_to_resolve,
                            end_position_id=end_pos_id,
                        )
                    )
                self.current_state = VehicleState.ONLINE
                self.current_drive_id = None
                self.drive_start_time = None
                self.drive_start_odometer = None
                self.drive_start_geocoded = False

        # 4. Charging Session State Machine & Real-time Curve Tracking
        if self.current_state != VehicleState.DRIVING:
            if self._is_charging_signal(point):
                if self.current_state != VehicleState.CHARGING:
                    # Ensure we have a valid position_id for charging_processes (NOT NULL in schema)
                    pos_id = inserted_pos_id or self.last_position_id
                    if pos_id is None and self.last_coords is not None:
                        synth_point = point.model_copy(
                            update={
                                "latitude": self.last_coords[0],
                                "longitude": self.last_coords[1],
                            }
                        )
                        pos_id = await self.repo.insert_position(
                            point=synth_point,
                            car_id=self.car_id,
                            drive_id=None,
                        )
                        if pos_id is not None:
                            self.last_position_id = pos_id

                    if pos_id is not None:
                        logger.info(
                            "⚡ [CHARGE START DETECTED] State: %s, Voltage: %sV, Current: %sA",
                            point.charge_state,
                            point.charger_voltage or self.last_charger_voltage,
                            point.charger_actual_current or self.last_charger_current,
                        )
                        self.current_state = VehicleState.CHARGING
                        self.charge_start_time = now
                        self.charge_energy_added_kwh = (
                            point.charge_energy_added
                            if point.charge_energy_added is not None
                            else Decimal("0.00")
                        )
                        self.last_charge_sample_time = now
                        self.current_charging_process_id = await self.repo.start_charging_process(
                            car_id=self.car_id,
                            start_time=now,
                            position_id=pos_id,
                            start_battery_level=point.battery_level or self.last_battery_level,
                            start_ideal_range_km=point.ideal_battery_range_km
                            or self.last_ideal_range_km,
                            start_rated_range_km=point.rated_battery_range_km
                            or self.last_rated_range_km,
                        )
                        CHARGES_DETECTED.labels(event="start").inc()
                        if (
                            self.current_charging_process_id is not None
                            and self.last_coords is not None
                        ):
                            self._spawn_background(
                                self._resolve_charging_address(
                                    charging_process_id=self.current_charging_process_id,
                                    latitude=self.last_coords[0],
                                    longitude=self.last_coords[1],
                                )
                            )

                # Record charging curve point if session is active
                if (
                    self.current_state == VehicleState.CHARGING
                    and self.current_charging_process_id is not None
                ):
                    power_kw = self._compute_charger_power_kw(point)
                    self.last_charger_power_kw = power_kw

                    if point.charge_energy_added is not None:
                        self.charge_energy_added_kwh = point.charge_energy_added
                    elif self.last_charge_sample_time is not None and power_kw > 0:
                        dt_hours = max(
                            0.0, (now - self.last_charge_sample_time).total_seconds() / 3600.0
                        )
                        if dt_hours > 0:
                            delta_kwh = Decimal(str(round(power_kw * dt_hours, 4)))
                            self.charge_energy_added_kwh = (
                                self.charge_energy_added_kwh + delta_kwh
                            ).quantize(Decimal("0.01"))

                    self.last_charge_sample_time = now

                    enriched_point = point.model_copy(
                        update={
                            "battery_level": point.battery_level or self.last_battery_level,
                            "ideal_battery_range_km": point.ideal_battery_range_km
                            or self.last_ideal_range_km,
                            "rated_battery_range_km": point.rated_battery_range_km
                            or self.last_rated_range_km,
                            "charger_voltage": point.charger_voltage or self.last_charger_voltage,
                            "charger_actual_current": point.charger_actual_current
                            if point.charger_actual_current is not None
                            else self.last_charger_current,
                        }
                    )
                    await self.repo.insert_charge(
                        charging_process_id=self.current_charging_process_id,
                        point=enriched_point,
                        charge_energy_added=self.charge_energy_added_kwh,
                        charger_power=power_kw,
                    )

            elif self.current_state == VehicleState.CHARGING and self._is_charging_stopped_signal(
                point, is_in_motion
            ):
                logger.info(
                    "🔌 [CHARGE END DETECTED] State: %s, Final kWh: %s",
                    point.charge_state,
                    self.charge_energy_added_kwh,
                )
                await self._close_active_charging_session(now, point)
                self.current_state = VehicleState.ONLINE

        self.last_point = point
