from typing import List, Literal, Tuple
from pydantic import BaseModel, Field, field_validator


class CoordinateValidator:
    @staticmethod
    def validate_coord(coord: Tuple[float, float]) -> Tuple[float, float]:
        lon, lat = coord
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude {lon} out of valid range [-180, 180]")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} out of valid range [-90, 90]")
        return (lon, lat)


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: Tuple[float, float] = Field(
        ...,
        description="Coordinates in [longitude, latitude] order"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        return CoordinateValidator.validate_coord(v)


class LineStringGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: List[Tuple[float, float]] = Field(
        ...,
        min_length=2,
        description="List of [longitude, latitude] coordinate pairs"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        for pt in v:
            CoordinateValidator.validate_coord(pt)
        return v


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[Tuple[float, float]]] = Field(
        ...,
        description="Linear rings of coordinates in [longitude, latitude] order"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, rings: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("Polygon linear ring must contain at least 4 coordinate pairs")
            if ring[0] != ring[-1]:
                raise ValueError("Polygon linear ring must be closed (first and last coordinate must match)")
            for pt in ring:
                CoordinateValidator.validate_coord(pt)
        return rings


class MultiPolygonGeometry(BaseModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: List[List[List[Tuple[float, float]]]] = Field(
        ...,
        description="List of polygons"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(
        cls, polygons: List[List[List[Tuple[float, float]]]]
    ) -> List[List[List[Tuple[float, float]]]]:
        for rings in polygons:
            for ring in rings:
                if len(ring) < 4:
                    raise ValueError("MultiPolygon linear ring must contain at least 4 coordinate pairs")
                if ring[0] != ring[-1]:
                    raise ValueError("MultiPolygon linear ring must be closed")
                for pt in ring:
                    CoordinateValidator.validate_coord(pt)
        return polygons
