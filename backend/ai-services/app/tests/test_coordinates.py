import pytest
from app.schemas.geojson import (
    PointGeometry,
    LineStringGeometry,
    PolygonGeometry,
    CoordinateValidator,
)


def test_valid_coordinates():
    lon, lat = CoordinateValidator.validate_coord((80.27, 13.08))
    assert lon == 80.27
    assert lat == 13.08


def test_invalid_longitude():
    with pytest.raises(ValueError, match="Longitude"):
        CoordinateValidator.validate_coord((185.0, 13.0))


def test_invalid_latitude():
    with pytest.raises(ValueError, match="Latitude"):
        CoordinateValidator.validate_coord((80.0, 95.0))


def test_point_geometry_valid():
    pt = PointGeometry(coordinates=(82.2, 16.9))
    assert pt.type == "Point"
    assert pt.coordinates == (82.2, 16.9)


def test_linestring_geometry_valid():
    line = LineStringGeometry(coordinates=[(80.0, 12.0), (80.5, 12.5), (81.0, 13.0)])
    assert line.type == "LineString"
    assert len(line.coordinates) == 3


def test_polygon_geometry_unclosed_ring_fails():
    with pytest.raises(ValueError, match="must be closed"):
        PolygonGeometry(
            coordinates=[
                [(80.0, 12.0), (81.0, 12.0), (81.0, 13.0), (80.0, 12.5)]  # Not closed
            ]
        )


def test_polygon_geometry_valid():
    poly = PolygonGeometry(
        coordinates=[
            [(80.0, 12.0), (81.0, 12.0), (81.0, 13.0), (80.0, 13.0), (80.0, 12.0)]
        ]
    )
    assert poly.type == "Polygon"
    assert len(poly.coordinates[0]) == 5
