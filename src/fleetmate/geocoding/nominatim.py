import asyncio
import logging
import time
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, Field

from fleetmate.config.settings import settings
from fleetmate.metrics.prometheus import GEOCODING_REQUESTS

logger = logging.getLogger(__name__)


class ResolvedAddress(BaseModel):
    """
    Normalized street address record mapped from Nominatim JSONv2 response,
    designed for direct insertion into PostgreSQL public.addresses.
    """

    osm_id: int
    osm_type: str
    display_name: str | None = None
    latitude: Decimal
    longitude: Decimal
    name: str | None = None
    house_number: str | None = None
    road: str | None = None
    neighbourhood: str | None = None
    city: str | None = None
    county: str | None = None
    postcode: str | None = None
    state: str | None = None
    state_district: str | None = None
    country: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_nominatim_json(
        cls,
        data: dict[str, Any],
        fallback_lat: Decimal,
        fallback_lon: Decimal,
    ) -> "ResolvedAddress | None":
        """
        Parses an OpenStreetMap Nominatim reverse-geocoding JSONv2 payload.
        """
        osm_id = data.get("osm_id")
        osm_type = data.get("osm_type")
        if osm_id is None or not osm_type:
            return None

        addr = data.get("address") or {}
        if not isinstance(addr, dict):
            addr = {}

        def _trunc(val: Any, max_len: int = 255) -> str | None:
            if val is None or val == "":
                return None
            return str(val)[:max_len]

        try:
            lat = Decimal(str(data.get("lat", fallback_lat))).quantize(Decimal("0.000001"))
        except Exception:
            lat = fallback_lat.quantize(Decimal("0.000001"))

        try:
            lon = Decimal(str(data.get("lon", fallback_lon))).quantize(Decimal("0.000001"))
        except Exception:
            lon = fallback_lon.quantize(Decimal("0.000001"))

        name_val = (
            data.get("name")
            or addr.get("amenity")
            or addr.get("building")
            or addr.get("shop")
            or addr.get("leisure")
            or addr.get("tourism")
            or addr.get("office")
        )
        road_val = (
            addr.get("road")
            or addr.get("pedestrian")
            or addr.get("footway")
            or addr.get("path")
            or addr.get("cycleway")
        )
        neighbourhood_val = (
            addr.get("neighbourhood")
            or addr.get("suburb")
            or addr.get("quarter")
            or addr.get("residential")
        )
        city_val = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("municipality")
            or addr.get("hamlet")
        )

        return cls(
            osm_id=int(osm_id),
            osm_type=str(osm_type),
            display_name=_trunc(data.get("display_name"), 512),
            latitude=lat,
            longitude=lon,
            name=_trunc(name_val),
            house_number=_trunc(addr.get("house_number")),
            road=_trunc(road_val),
            neighbourhood=_trunc(neighbourhood_val),
            city=_trunc(city_val),
            county=_trunc(addr.get("county")),
            postcode=_trunc(addr.get("postcode")),
            state=_trunc(addr.get("state") or addr.get("province")),
            state_district=_trunc(addr.get("state_district")),
            country=_trunc(addr.get("country")),
            raw=addr,
        )


class NominatimGeocoder:
    """
    Asynchronous, rate-limited reverse geocoding client for OpenStreetMap Nominatim.
    Strictly enforces Nominatim usage policy (custom User-Agent, <= 1 req/sec).
    """

    def __init__(
        self,
        base_url: str | None = None,
        user_agent: str | None = None,
        rate_limit_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.nominatim_base_url).rstrip("/")
        self.user_agent = user_agent or settings.nominatim_user_agent
        self.rate_limit_seconds = (
            rate_limit_seconds
            if rate_limit_seconds is not None
            else settings.nominatim_rate_limit_seconds
        )
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    async def reverse_geocode(
        self,
        latitude: Decimal | float,
        longitude: Decimal | float,
    ) -> ResolvedAddress | None:
        """
        Resolves (latitude, longitude) into a structured ResolvedAddress.
        Returns None if geocoding is disabled or if the lookup fails.
        """
        if not settings.geocoding_enabled:
            return None

        lat_dec = Decimal(str(latitude))
        lon_dec = Decimal(str(longitude))

        async with self._lock:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.rate_limit_seconds and self._last_request_time > 0:
                await asyncio.sleep(self.rate_limit_seconds - elapsed)

            url = f"{self.base_url}/reverse"
            params = {
                "format": "jsonv2",
                "lat": f"{lat_dec:.6f}",
                "lon": f"{lon_dec:.6f}",
                "addressdetails": "1",
                "zoom": "18",
            }
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params, headers=headers)
                    self._last_request_time = time.monotonic()
                    response.raise_for_status()
                    payload = response.json()

                if not isinstance(payload, dict) or "error" in payload:
                    GEOCODING_REQUESTS.labels(status="not_found").inc()
                    logger.warning(
                        "Nominatim returned no result for (%s, %s): %s",
                        lat_dec,
                        lon_dec,
                        payload,
                    )
                    return None

                resolved = ResolvedAddress.from_nominatim_json(
                    data=payload,
                    fallback_lat=lat_dec,
                    fallback_lon=lon_dec,
                )
                if resolved:
                    GEOCODING_REQUESTS.labels(status="success").inc()
                    logger.info(
                        "Resolved coordinates (%s, %s) -> %s",
                        lat_dec,
                        lon_dec,
                        resolved.display_name or resolved.road or resolved.city,
                    )
                else:
                    GEOCODING_REQUESTS.labels(status="invalid_payload").inc()
                return resolved
            except Exception as e:
                self._last_request_time = time.monotonic()
                GEOCODING_REQUESTS.labels(status="error").inc()
                logger.error(
                    "Reverse geocoding failed for (%s, %s): %s",
                    lat_dec,
                    lon_dec,
                    e,
                )
                return None
