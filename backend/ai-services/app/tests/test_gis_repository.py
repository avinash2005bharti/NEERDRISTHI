import pytest
from app.repositories.gis_repository import GISRepository


@pytest.mark.asyncio
async def test_find_nearest_pfz_unconfigured_db_returns_empty_list():
    repo = GISRepository(db_getter=lambda: None)
    results = await repo.find_nearest_pfz(80.25, 13.05)
    assert results == []


@pytest.mark.asyncio
async def test_find_restricted_intersections_unconfigured_returns_empty_list():
    repo = GISRepository(db_getter=lambda: None)
    results = await repo.find_restricted_zone_intersections(
        {"type": "Point", "coordinates": [80.25, 13.05]}
    )
    assert results == []


@pytest.mark.asyncio
async def test_find_nearest_pfz_invalid_coordinates_raises():
    repo = GISRepository(db_getter=lambda: None)
    with pytest.raises(ValueError):
        await repo.find_nearest_pfz(200.0, 13.05)
