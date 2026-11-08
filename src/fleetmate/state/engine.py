import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fleetmate.config.settings import settings
from fleetmate.geocoding.nominatim import NominatimGeocoder
from fleetmate.metrics.prometheus import DRIVES_DETECTED
from fleetmate.storage.postgres import TeslaMateRepository
from fleetmate.telemetry.models import VehicleTelemetryPoint

logger = logging.getLogger(__name__)


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
        repo: TeslaMateRepository,
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
        self.last_point: VehicleTelemetryPoint | None = None
        self.last_coords: tuple[Decimal, Decimal] | None = None
        self.last_position_id: int | None = None
        self.last_motion_time: datetime | None = None
        self._background_tasks: set[asyncio.Task[None]] = set()

    def _spawn_background(self, coro) -> None:
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
        resolved = await self.geocoder.reverse_geocode(latitude, longitude)
        address_id = await self.repo.upsert_address(resolved) if resolved else None
        await self.repo.update_drive_start_location(
            drive_id=drive_id,
            address_id=address_id,
            position_id=position_id,
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
        if coords is not None:
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
        )

    async def process_point(self, point: VehicleTelemetryPoint) -> None:
        """
        Processes a single incoming telemetry point, updates state machine,
        and coordinates persistence into PostgreSQL.
        """
        now = point.timestamp
        if point.latitude is not None and point.longitude is not None:
            self.last_coords = (point.latitude, point.longitude)

        # Determine motion & gear
        is_in_motion = (point.speed is not None and point.speed > 0) or (point.gear in ["D", "R"])

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

        self.last_point = point
