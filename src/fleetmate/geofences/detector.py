import math
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

EARTH_RADIUS_METERS = 6_371_000.0


class GeofenceRecord(BaseModel):
    """
    Represents a user-defined circular geofence zone from public.geofences.
    """

    id: int
    name: str
    latitude: Decimal
    longitude: Decimal
    radius: int = 25  # meters
    cost_per_unit: Decimal | None = None
    session_fee: Decimal | None = None
    billing_type: Literal["per_kwh", "per_minute"] = "per_kwh"


def haversine_distance_meters(
    lat1: float | Decimal,
    lon1: float | Decimal,
    lat2: float | Decimal,
    lon2: float | Decimal,
) -> float:
    """
    Calculates the great-circle distance in meters between two WGS84 coordinates
    using the Haversine formula.
    """
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))

    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_METERS * c


def find_matching_geofence(
    latitude: Decimal | float,
    longitude: Decimal | float,
    geofences: Sequence[GeofenceRecord],
) -> GeofenceRecord | None:
    """
    Finds the closest geofence whose radius encompasses (latitude, longitude).
    Returns None if the coordinate does not fall inside any configured geofence.
    """
    best_match: GeofenceRecord | None = None
    best_distance: float = float("inf")

    for gf in geofences:
        dist = haversine_distance_meters(latitude, longitude, gf.latitude, gf.longitude)
        if dist <= float(gf.radius) and dist < best_distance:
            best_match = gf
            best_distance = dist

    return best_match


def calculate_charging_cost(
    geofence: GeofenceRecord | None,
    charge_energy_added_kwh: Decimal | None,
    charge_energy_used_kwh: Decimal | None = None,
    duration_min: int | None = None,
) -> Decimal | None:
    """
    Computes total charging session cost based on the matched geofence tariff:
    - 'per_kwh': (energy_kwh * cost_per_unit) + session_fee
    - 'per_minute': (duration_min * cost_per_unit) + session_fee
    Returns None if no geofence or tariff is configured.
    """
    if geofence is None:
        return None
    if geofence.cost_per_unit is None and geofence.session_fee is None:
        return None

    rate = geofence.cost_per_unit or Decimal("0.0000")
    fee = geofence.session_fee or Decimal("0.00")

    if geofence.billing_type == "per_minute":
        minutes = Decimal(str(max(0, duration_min or 0)))
        total = (minutes * rate) + fee
    else:
        billable_kwh = (
            charge_energy_used_kwh
            if (charge_energy_used_kwh is not None and charge_energy_used_kwh > 0)
            else (charge_energy_added_kwh or Decimal("0.00"))
        )
        total = (max(Decimal("0.00"), billable_kwh) * rate) + fee

    return total.quantize(Decimal("0.01"))
