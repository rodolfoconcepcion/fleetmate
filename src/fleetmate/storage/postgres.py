import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import asyncpg

from fleetmate.config.settings import settings
from fleetmate.geocoding.nominatim import ResolvedAddress
from fleetmate.geofences.detector import GeofenceRecord, find_matching_geofence
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

    async def upsert_address(self, addr: ResolvedAddress) -> int | None:
        """
        Upserts a resolved Nominatim address into public.addresses.
        Reuses existing address rows matching (osm_id, osm_type).
        Returns the address ID.
        """
        if not self.pool:
            return None

        now = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
        query = """
            INSERT INTO public.addresses (
                osm_id, osm_type, display_name, latitude, longitude,
                name, house_number, road, neighbourhood, city,
                county, postcode, state, state_district, country,
                raw, inserted_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15,
                $16::jsonb, $17, $17
            )
            ON CONFLICT (osm_id, osm_type) DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, public.addresses.display_name),
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """
        try:
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    addr.osm_id,
                    addr.osm_type,
                    addr.display_name,
                    addr.latitude,
                    addr.longitude,
                    addr.name,
                    addr.house_number,
                    addr.road,
                    addr.neighbourhood,
                    addr.city,
                    addr.county,
                    addr.postcode,
                    addr.state,
                    addr.state_district,
                    addr.country,
                    json.dumps(addr.raw),
                    now,
                )
                return record["id"] if record else None
        except Exception as e:
            logger.error("Failed to upsert address into DB: %s", e)
            return None

    async def find_geofence(
        self,
        latitude: Decimal,
        longitude: Decimal,
    ) -> GeofenceRecord | None:
        """
        Loads all configured geofences from public.geofences and returns the
        closest matching GeofenceRecord whose radius contains (latitude, longitude).
        """
        if not self.pool:
            return None

        query = """
            SELECT
                id, name, latitude, longitude, radius,
                cost_per_unit, session_fee, billing_type::text AS billing_type
            FROM public.geofences;
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                geofences = [
                    GeofenceRecord(
                        id=r["id"],
                        name=r["name"],
                        latitude=r["latitude"],
                        longitude=r["longitude"],
                        radius=r["radius"],
                        cost_per_unit=r["cost_per_unit"],
                        session_fee=r["session_fee"],
                        billing_type=r["billing_type"] or "per_kwh",
                    )
                    for r in rows
                ]
                return find_matching_geofence(latitude, longitude, geofences)
        except Exception as e:
            logger.error("Failed to query geofences from DB: %s", e)
            return None

    async def update_drive_start_location(
        self,
        drive_id: int,
        address_id: int | None = None,
        position_id: int | None = None,
        geofence_id: int | None = None,
    ) -> None:
        """
        Links start_address_id, start_position_id, and/or start_geofence_id to an active drive.
        """
        if not self.pool:
            return

        query = """
            UPDATE public.drives
            SET start_address_id = COALESCE($2, start_address_id),
                start_position_id = COALESCE($3, start_position_id),
                start_geofence_id = COALESCE($4, start_geofence_id)
            WHERE id = $1;
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, drive_id, address_id, position_id, geofence_id)
        except Exception as e:
            logger.error("Failed to update start location for drive #%d: %s", drive_id, e)

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
        end_address_id: int | None = None,
        end_position_id: int | None = None,
        end_geofence_id: int | None = None,
    ) -> None:
        """
        Finalizes an existing drive in public.drives with calculated stats,
        position bounds, resolved end address, and matched end geofence.
        """
        if not self.pool:
            return

        distance = None
        if end_odometer is not None and start_odometer is not None:
            distance = max(0.0, end_odometer - start_odometer)

        query = """
            WITH drive_stats AS (
                SELECT
                    MAX(speed)::smallint AS speed_max,
                    MAX(power)::smallint AS power_max,
                    MIN(power)::smallint AS power_min,
                    ROUND(AVG(outside_temp), 1) AS outside_temp_avg,
                    ROUND(AVG(inside_temp), 1) AS inside_temp_avg,
                    MIN(id) AS first_pos_id,
                    MAX(id) AS last_pos_id
                FROM public.positions
                WHERE drive_id = $1
            )
            UPDATE public.drives d
            SET end_date = $2,
                end_km = $3,
                end_ideal_range_km = $4,
                end_rated_range_km = $5,
                distance = COALESCE($6, d.distance),
                end_address_id = COALESCE($7, d.end_address_id),
                start_position_id = COALESCE(d.start_position_id, ds.first_pos_id),
                end_position_id = COALESCE($8, ds.last_pos_id),
                end_geofence_id = COALESCE($9, d.end_geofence_id),
                duration_min = GREATEST(0, ROUND(EXTRACT(EPOCH FROM ($2 - d.start_date)) / 60.0))::smallint,
                speed_max = COALESCE(ds.speed_max, d.speed_max),
                power_max = COALESCE(ds.power_max, d.power_max),
                power_min = COALESCE(ds.power_min, d.power_min),
                outside_temp_avg = COALESCE(ds.outside_temp_avg, d.outside_temp_avg),
                inside_temp_avg = COALESCE(ds.inside_temp_avg, d.inside_temp_avg)
            FROM drive_stats ds
            WHERE d.id = $1;
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
                    end_address_id,
                    end_position_id,
                    end_geofence_id,
                )
                logger.info("Finalized drive #%d in TeslaMate DB.", drive_id)
        except Exception as e:
            logger.error("Failed to end drive #%d in TeslaMate DB: %s", drive_id, e)

    async def start_charging_process(
        self,
        car_id: int,
        start_time: datetime,
        position_id: int,
        start_battery_level: int | None = None,
        start_ideal_range_km: Decimal | None = None,
        start_rated_range_km: Decimal | None = None,
        address_id: int | None = None,
        geofence_id: int | None = None,
    ) -> int | None:
        """
        Initializes a new charging session in public.charging_processes.
        Requires a non-null position_id per PostgreSQL schema constraints.
        """
        if not self.pool:
            return None

        query = """
            INSERT INTO public.charging_processes (
                car_id, start_date, position_id,
                start_battery_level, start_ideal_range_km, start_rated_range_km,
                address_id, geofence_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id;
        """
        try:
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    car_id,
                    start_time.replace(tzinfo=None),
                    position_id,
                    start_battery_level,
                    start_ideal_range_km,
                    start_rated_range_km,
                    address_id,
                    geofence_id,
                )
                return record["id"] if record else None
        except Exception as e:
            logger.error("Failed to start charging process in DB: %s", e)
            return None

    async def update_charging_process_address(
        self,
        charging_process_id: int,
        address_id: int | None = None,
        geofence_id: int | None = None,
    ) -> None:
        """
        Links a resolved Nominatim address_id and/or geofence_id to an active charging_process.
        """
        if not self.pool or (address_id is None and geofence_id is None):
            return

        query = """
            UPDATE public.charging_processes
            SET address_id = COALESCE($2, address_id),
                geofence_id = COALESCE($3, geofence_id)
            WHERE id = $1;
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, charging_process_id, address_id, geofence_id)
        except Exception as e:
            logger.error(
                "Failed to update address/geofence for charging_process #%d: %s",
                charging_process_id,
                e,
            )

    async def insert_charge(
        self,
        charging_process_id: int,
        point: VehicleTelemetryPoint,
        charge_energy_added: Decimal,
        charger_power: int,
    ) -> int | None:
        """
        Inserts a single charging curve data point into public.charges.
        Respects NOT NULL constraints on charge_energy_added, charger_power,
        and ideal_battery_range_km, and CHECK (charger_phases > 0).
        """
        if not self.pool:
            return None

        ideal_range = (
            point.ideal_battery_range_km
            or point.rated_battery_range_km
            or point.est_battery_range_km
            or Decimal("0.0")
        )
        phases = (
            point.charger_phases
            if (point.charger_phases is not None and point.charger_phases > 0)
            else None
        )

        query = """
            INSERT INTO public.charges (
                date, charging_process_id, battery_level, usable_battery_level,
                charge_energy_added, charger_actual_current, charger_phases,
                charger_pilot_current, charger_power, charger_voltage,
                fast_charger_present, conn_charge_cable, fast_charger_brand,
                fast_charger_type, ideal_battery_range_km, rated_battery_range_km,
                outside_temp, battery_heater_on, battery_heater
            ) VALUES (
                $1, $2, $3, $4,
                $5, $6, $7,
                $8, $9, $10,
                $11, $12, $13,
                $14, $15, $16,
                $17, $18, $18
            ) RETURNING id;
        """
        try:
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    point.timestamp.replace(tzinfo=None),
                    charging_process_id,
                    point.battery_level,
                    point.usable_battery_level,
                    charge_energy_added,
                    point.charger_actual_current,
                    phases,
                    point.charger_pilot_current,
                    charger_power,
                    point.charger_voltage,
                    point.fast_charger_present,
                    point.conn_charge_cable,
                    point.fast_charger_brand,
                    point.fast_charger_type,
                    ideal_range,
                    point.rated_battery_range_km,
                    point.outside_temp,
                    point.battery_heater_on,
                )
                return record["id"] if record else None
        except Exception as e:
            logger.error("Failed to insert charge point into DB: %s", e)
            return None

    async def end_charging_process(
        self,
        charging_process_id: int,
        end_time: datetime,
        end_battery_level: int | None = None,
        end_ideal_range_km: Decimal | None = None,
        end_rated_range_km: Decimal | None = None,
        charge_energy_added: Decimal | None = None,
        address_id: int | None = None,
        geofence_id: int | None = None,
        cost: Decimal | None = None,
    ) -> None:
        """
        Finalizes an active charging session in public.charging_processes,
        aggregating duration, energy added, final SoC, average outside temperature,
        matched geofence_id, and calculated electricity cost.
        """
        if not self.pool:
            return

        query = """
            WITH charge_stats AS (
                SELECT
                    MAX(charge_energy_added) AS max_energy_added,
                    ROUND(AVG(outside_temp), 1) AS outside_temp_avg,
                    (ARRAY_AGG(battery_level ORDER BY date DESC) FILTER (WHERE battery_level IS NOT NULL))[1] AS last_soc,
                    (ARRAY_AGG(ideal_battery_range_km ORDER BY date DESC) FILTER (WHERE ideal_battery_range_km IS NOT NULL))[1] AS last_ideal_range,
                    (ARRAY_AGG(rated_battery_range_km ORDER BY date DESC) FILTER (WHERE rated_battery_range_km IS NOT NULL))[1] AS last_rated_range
                FROM public.charges
                WHERE charging_process_id = $1
            )
            UPDATE public.charging_processes cp
            SET end_date = $2,
                end_battery_level = COALESCE($3, cs.last_soc, cp.end_battery_level),
                end_ideal_range_km = COALESCE($4, cs.last_ideal_range, cp.end_ideal_range_km),
                end_rated_range_km = COALESCE($5, cs.last_rated_range, cp.end_rated_range_km),
                charge_energy_added = COALESCE($6, cs.max_energy_added, cp.charge_energy_added, 0.00),
                address_id = COALESCE($7, cp.address_id),
                geofence_id = COALESCE($8, cp.geofence_id),
                cost = COALESCE($9, cp.cost),
                duration_min = GREATEST(0, ROUND(EXTRACT(EPOCH FROM ($2 - cp.start_date)) / 60.0))::smallint,
                outside_temp_avg = COALESCE(cs.outside_temp_avg, cp.outside_temp_avg)
            FROM charge_stats cs
            WHERE cp.id = $1;
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    charging_process_id,
                    end_time.replace(tzinfo=None),
                    end_battery_level,
                    end_ideal_range_km,
                    end_rated_range_km,
                    charge_energy_added,
                    address_id,
                    geofence_id,
                    cost,
                )
                logger.info(
                    "Finalized charging_process #%d in DB.",
                    charging_process_id,
                )
        except Exception as e:
            logger.error(
                "Failed to end charging_process #%d in DB: %s",
                charging_process_id,
                e,
            )
