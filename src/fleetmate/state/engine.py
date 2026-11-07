import logging
from datetime import datetime
from enum import StrEnum

from fleetmate.config.settings import settings
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
    TeslaMate trip boundaries (drives & charges) with zero API polling.
    """

    def __init__(self, repo: TeslaMateRepository, car_id: int = settings.car_id) -> None:
        self.repo = repo
        self.car_id = car_id
        self.current_state: VehicleState = VehicleState.ONLINE
        self.current_drive_id: int | None = None
        self.drive_start_time: datetime | None = None
        self.drive_start_odometer: float | None = None
        self.last_point: VehicleTelemetryPoint | None = None
        self.last_motion_time: datetime | None = None

    async def process_point(self, point: VehicleTelemetryPoint) -> None:
        """
        Processes a single incoming telemetry point, updates state machine,
        and coordinates persistence into TeslaMate PostgreSQL.
        """
        now = point.timestamp

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
                self.current_drive_id = await self.repo.start_drive(
                    car_id=self.car_id,
                    start_time=now,
                    start_odometer=point.odometer,
                    start_ideal_range_km=point.ideal_battery_range_km,
                    start_rated_range_km=point.rated_battery_range_km,
                )
                logger.info("Created new drive #%s in TeslaMate database.", self.current_drive_id)

        # 2. Drive End Detection Transition (Parked or idle timeout)
        elif self.current_state == VehicleState.DRIVING:
            idle_seconds = (
                (now - self.last_motion_time).total_seconds() if self.last_motion_time else 0
            )
            # If shifted to Park ('P') or idle for more than drive_idle_timeout_seconds
            if point.gear == "P" or idle_seconds > settings.drive_idle_timeout_seconds:
                logger.info(
                    "🅿️ [DRIVE END DETECTED] Vehicle parked (Gear: %s, Idle: %0.1fs)",
                    point.gear,
                    idle_seconds,
                )
                if self.current_drive_id:
                    await self.repo.end_drive(
                        drive_id=self.current_drive_id,
                        end_time=now,
                        end_odometer=point.odometer,
                        end_ideal_range_km=point.ideal_battery_range_km,
                        end_rated_range_km=point.rated_battery_range_km,
                        start_odometer=self.drive_start_odometer,
                    )
                self.current_state = VehicleState.ONLINE
                self.current_drive_id = None
                self.drive_start_time = None
                self.drive_start_odometer = None

        # 3. Always insert valid coordinate points
        if point.latitude is not None and point.longitude is not None:
            await self.repo.insert_position(
                point=point,
                car_id=self.car_id,
                drive_id=self.current_drive_id,
            )

        self.last_point = point
