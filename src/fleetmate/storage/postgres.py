import logging
from datetime import datetime
from decimal import Decimal

import asyncpg

from fleetmate.config.settings import settings
from fleetmate.telemetry.models import VehicleTelemetryPoint

logger = logging.getLogger(__name__)


class TeslaMateRepository:
    """
    High-performance asyncpg repository directly inserting into TeslaMate PostgreSQL schema:
    - public.positions
    - public.drives
    - public.charges / charging_processes
    - public.states
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}@"
            f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        logger.info(
            "Connecting to TeslaMate PostgreSQL database at %s:%s...",
            settings.postgres_host,
            settings.postgres_port,
        )
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=settings.postgres_pool_min_size,
            max_size=settings.postgres_pool_max_size,
            timeout=10.0,
        )
        logger.info("TeslaMate PostgreSQL connection pool established successfully.")

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            logger.info("TeslaMate PostgreSQL connection pool closed.")

    async def insert_position(
        self,
        point: VehicleTelemetryPoint,
        car_id: int,
        drive_id: int | None = None,
    ) -> int | None:
        """
        Inserts a single high-resolution position record into public.positions.
        Returns the generated position ID.
        """
        if not self.pool or point.latitude is None or point.longitude is None:
            return None

        query = """
            INSERT INTO public.positions (
                date, latitude, longitude, speed, power, odometer,
                ideal_battery_range_km, battery_level, outside_temp, inside_temp,
                rated_battery_range_km, est_battery_range_km, usable_battery_level,
                tpms_pressure_fl, tpms_pressure_fr, tpms_pressure_rl, tpms_pressure_rr,
                is_climate_on, car_id, drive_id
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13,
                $14, $15, $16, $17,
                $18, $19, $20
            ) RETURNING id;
        """

        try:
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    point.timestamp.replace(tzinfo=None),
                    point.latitude,
                    point.longitude,
                    point.speed,
                    point.power,
                    point.odometer,
                    point.ideal_battery_range_km,
                    point.battery_level,
                    point.outside_temp,
                    point.inside_temp,
                    point.rated_battery_range_km,
                    point.est_battery_range_km,
                    point.usable_battery_level,
                    point.tpms_pressure_fl,
                    point.tpms_pressure_fr,
                    point.tpms_pressure_rl,
                    point.tpms_pressure_rr,
                    point.is_climate_on,
                    car_id,
                    drive_id,
                )
                return record["id"] if record else None
        except Exception as e:
            logger.error("Failed to insert position into TeslaMate DB: %s", e)
            return None

    async def start_drive(
        self,
        car_id: int,
        start_time: datetime,
        start_odometer: float | None,
        start_ideal_range_km: Decimal | None,
        start_rated_range_km: Decimal | None,
    ) -> int | None:
        """
        Initializes a new trip entry in public.drives.
        """
        if not self.pool:
            return None

        query = """
            INSERT INTO public.drives (
                car_id, start_date, start_km, start_ideal_range_km, start_rated_range_km
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id;
        """
        try:
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    car_id,
                    start_time.replace(tzinfo=None),
                    start_odometer,
                    start_ideal_range_km,
                    start_rated_range_km,
                )
                return record["id"] if record else None
        except Exception as e:
            logger.error("Failed to start drive in TeslaMate DB: %s", e)
            return None

    async def end_drive(
        self,
        drive_id: int,
        end_time: datetime,
        end_odometer: float | None,
        end_ideal_range_km: Decimal | None,
        end_rated_range_km: Decimal | None,
        start_odometer: float | None = None,
    ) -> None:
        """
        Finalizes an existing drive in public.drives with calculated stats.
        """
        if not self.pool:
            return

        distance = None
        if end_odometer is not None and start_odometer is not None:
            distance = max(0.0, end_odometer - start_odometer)

        query = """
            UPDATE public.drives
            SET end_date = $2,
                end_km = $3,
                end_ideal_range_km = $4,
                end_rated_range_km = $5,
                distance = COALESCE($6, distance)
            WHERE id = $1;
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    drive_id,
                    end_time.replace(tzinfo=None),
                    end_odometer,
                    end_ideal_range_km,
                    end_rated_range_km,
                    distance,
                )
                logger.info("Finalized drive #%d in TeslaMate DB.", drive_id)
        except Exception as e:
            logger.error("Failed to end drive #%d in TeslaMate DB: %s", drive_id, e)
