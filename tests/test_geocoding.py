import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from fleetmate.geocoding.nominatim import NominatimGeocoder, ResolvedAddress
from fleetmate.state.engine import StateMachineEngine
from fleetmate.telemetry.models import VehicleTelemetryPoint


def test_resolved_address_from_nominatim_json():
    sample_payload = {
        "place_id": 100200300,
        "osm_type": "way",
        "osm_id": 987654321,
        "lat": "39.781721",
        "lon": "-89.650148",
        "name": "Central Plaza",
        "display_name": "123, Main St, Downtown, Springfield, Sangamon County, Illinois, 62701, United States",
        "address": {
            "house_number": "123",
            "road": "Main St",
            "neighbourhood": "Downtown",
            "city": "Springfield",
            "county": "Sangamon County",
            "state": "Illinois",
            "postcode": "62701",
            "country": "United States",
        },
    }

    addr = ResolvedAddress.from_nominatim_json(
        data=sample_payload,
        fallback_lat=Decimal("39.781700"),
        fallback_lon=Decimal("-89.650100"),
    )

    assert addr is not None
    assert addr.osm_id == 987654321
    assert addr.osm_type == "way"
    assert addr.house_number == "123"
    assert addr.road == "Main St"
    assert addr.city == "Springfield"
    assert addr.state == "Illinois"
    assert addr.postcode == "62701"
    assert addr.latitude == Decimal("39.781721")
    assert addr.longitude == Decimal("-89.650148")


@pytest.mark.asyncio
async def test_state_engine_geocodes_drive_start_and_end():
    repo = AsyncMock()
    repo.start_drive.return_value = 42
    repo.insert_position.side_effect = [101, 102]
    repo.upsert_address.side_effect = [501, 502]
    repo.find_geofence.return_value = None

    geocoder = AsyncMock(spec=NominatimGeocoder)
    geocoder.reverse_geocode.side_effect = [
        ResolvedAddress(
            osm_id=111,
            osm_type="way",
            display_name="123 Main St, Springfield",
            latitude=Decimal("39.781700"),
            longitude=Decimal("-89.650100"),
            road="Main St",
            city="Springfield",
        ),
        ResolvedAddress(
            osm_id=222,
            osm_type="way",
            display_name="456 Oak Ave, Shelbyville",
            latitude=Decimal("39.800000"),
            longitude=Decimal("-89.700000"),
            road="Oak Ave",
            city="Shelbyville",
        ),
    ]

    engine = StateMachineEngine(repo=repo, car_id=1, geocoder=geocoder)

    # 1. Start driving
    p1 = VehicleTelemetryPoint(
        vin="5YJ3E1EA1PF000001",
        latitude=Decimal("39.781700"),
        longitude=Decimal("-89.650100"),
        speed=35,
        gear="D",
        odometer=1000.0,
    )
    await engine.process_point(p1)
    await asyncio.gather(*list(engine._background_tasks))

    repo.start_drive.assert_awaited_once()
    repo.update_drive_start_location.assert_awaited_once_with(
        drive_id=42,
        address_id=501,
        position_id=101,
        geofence_id=None,
    )

    # 2. Park vehicle (Drive End)
    p2 = VehicleTelemetryPoint(
        vin="5YJ3E1EA1PF000001",
        latitude=Decimal("39.800000"),
        longitude=Decimal("-89.700000"),
        speed=0,
        gear="P",
        odometer=1012.5,
    )
    await engine.process_point(p2)
    await asyncio.gather(*list(engine._background_tasks))

    repo.end_drive.assert_awaited_once()
    call_kwargs = repo.end_drive.await_args.kwargs
    assert call_kwargs["drive_id"] == 42
    assert call_kwargs["end_address_id"] == 502
    assert call_kwargs["end_position_id"] == 102
