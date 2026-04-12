"""A module to write geojson files from napari shapes layers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import geojson
from geojson.geometry import Geometry, LineString, MultiPoint, Polygon
from napari.layers.shapes._shapes_models import Ellipse

if TYPE_CHECKING:
    from collections.abc import Sequence

    DataType = Any | Sequence[Any]
    FullLayerData = tuple[DataType, dict, str]


def write_shapes(path: str, layer_data: list[tuple[Any, dict, str]]) -> str:
    """Write a single geojson file from napari shape layer data."""
    with open(path, "w") as fp:
        shapes = []
        for layer in layer_data:
            data, meta, kind = layer
            if kind == "points":
                shapes.append(MultiPoint([list(p) for p in data]))
            else:
                shapes.extend(
                    [
                        get_geometry(s.tolist(), t)
                        for s, t in zip(data, meta["shape_type"])  # noqa E501
                    ]
                )

        # convert shapes into QuPath friendly format
        shapes = [format_qupath(s) for s in shapes]

        geojson.dump(geojson.FeatureCollection(shapes), fp)
        return fp.name


# TODO make explicit about how to change coordinates... it works for QuPath for now
def flip_coords(geom: Geometry, flipxy=True) -> list:
    """Return coordinates for geojson shapes."""
    if geom["type"] == "Point":
        geom["coordinates"].reverse()
        return geom
    else:
        for c in geom["coordinates"]:
            c.reverse()
    return geom


def format_qupath(shape, object_type="annotation", is_locked=False):
    """Convert to QuPath friendly object format."""
    shape = {
        "type": "Feature",
        "geometry": shape,
        "properties": {"object_type": object_type, "isLocked": is_locked},
    }
    if shape["geometry"]["type"] == "Polygon":
        shape["geometry"]["coordinates"] = [shape["geometry"]["coordinates"]]
    return shape


def get_geometry(coords: list, shape_type: str, flipxy=True) -> Polygon | LineString:
    """Get GeoJSON type geometry from napari shape."""
    if shape_type in ["rectangle", "polygon"]:
        shape = Polygon(coords)
    elif shape_type in ["line", "path"]:
        shape = LineString(coords)
    elif shape_type == "ellipse":
        shape = Polygon(ellipse_to_polygon(coords))
    else:
        raise ValueError(f"Shape type `{shape_type}` not supported.")
    if flipxy:
        shape = flip_coords(shape)
    return shape


def get_points(coords: list) -> MultiPoint:
    """Get GeoJSON MultiPoints from napari points layer."""
    ...


def ellipse_to_polygon(coords: list) -> list:
    """Convert an ellipse to a polygon."""
    # TODO implement custom function
    # Hacky way to use napari's internal conversion
    return Ellipse(coords)._edge_vertices.tolist()
