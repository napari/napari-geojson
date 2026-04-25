"""Read geojson files into napari."""

from __future__ import annotations

import warnings
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import geojson
import numpy as np
from geojson.geometry import Geometry, Polygon

if TYPE_CHECKING:
    import napari  # pragma: no cover


def napari_get_reader(path):
    """Get implementation of the napari_get_reader hook specification."""
    if isinstance(path, list):
        path = path[0]

    if not path.lower().endswith(".geojson"):
        return None

    return reader_function


def reader_function(path) -> list["napari.types.LayerDataTuple"]:
    """Take a path or list of paths and return a list of LayerData tuples."""
    # handle both a string and a list of strings
    paths = [path] if isinstance(path, str) else path
    layer_data_tuples = []
    for _path in paths:
        layer_data = geojson_to_napari(_path)
        layer_data_tuples.extend(layer_data)
    return layer_data_tuples


def geojson_to_napari(fname: str) -> list[tuple[Any, dict, str]]:
    """Convert geojson into napari shapes data."""
    with open(fname) as f:
        data = geojson.load(f)

    if isinstance(data, geojson.FeatureCollection):
        collection = data.features
    elif isinstance(data, geojson.GeometryCollection):
        collection = data.geometries
    elif isinstance(data, (geojson.Feature, Geometry)):
        collection = [data]
    # NOTE: Invalid geojson will be removed in 0.2.0
    # this is handling invalid geojson which was produced before 0.1.5
    else:
        warnings.warn(
            (
                "Invalid GeoJSON. Reading a non-standard top-level GeoJSON value (supported for backward compatibility with pre-0.1.5 output). "
                "Please use a Feature Collection, Geometry, or Feature. "
                "This fallback behavior will be removed in v0.2.0. "
            ),
            FutureWarning,
            stacklevel=2,
        )
        collection = data

    layer_data = []

    multi_point_geoms = []
    point_geoms = []
    shape_geoms = []
    shape_types = []

    for geom in collection:
        shape_type = get_shape_type(geom)
        if shape_type == "multipoint":
            multi_point_geoms.append(geom)
        elif shape_type == "points":
            point_geoms.append(geom)
        else:
            shape_geoms.append(geom)
            shape_types.append(shape_type)

    # create a point layer for each multipoint feature in the data
    for geom in multi_point_geoms:
        layer_data.append(create_point_layer_data([geom]))

    # all singleton points to a single layer
    if point_geoms:
        layer_data.append(create_point_layer_data(point_geoms))

    # create a single shape layer for all other shape geometries
    if shape_geoms:
        shapes = [get_coords(geom) for geom in shape_geoms]
        properties = get_properties(shape_geoms)
        meta = {"shape_type": shape_types, "properties": properties}
        layer_data.append((shapes, meta, "shapes"))

    return layer_data


def get_coords(geom: Geometry) -> np.ndarray:
    """Convert GeoJSON geometry coordinates to napari numpy arrays.

    GeoJSON is always in XY(Z optional) order (longitude, latitude,
    altitude), but napari expects ZYX order, so reverse the order of
    the last dimension of the coordinates.
    """
    coords = np.array(list(geojson.utils.coords(geom)))
    # Strip closing coordinate for polygons
    # GeoJSON requires closed rings per RFC 7946 §3.1.6
    # but napari expects just vertex coordinates
    geom_type = geom.geometry.type if geom.type == "Feature" else geom.type
    if (
        geom_type == "Polygon"
        and len(coords) > 1
        and np.array_equal(coords[0], coords[-1])
    ):
        coords = coords[:-1]

    return coords[..., ::-1]


def create_point_layer_data(collection) -> tuple[Any, dict, str]:
    pts = np.concatenate(
        [np.atleast_2d(get_coords(geom)) for geom in collection],
        axis=0,
    )
    pt_properties = get_properties(collection)
    pt_meta = {"properties": pt_properties}
    return (pts, pt_meta, "points")


def get_shape_type(geom: Geometry) -> str:
    """Translate geojson to napari shape notation."""
    if geom.type == "Feature":
        geom_type = geom.geometry.type
    else:
        geom_type = geom.type

    if geom_type == "Polygon":
        return "rectangle" if is_rectangle(geom) else "polygon"
    elif geom_type == "LineString":
        return "path" if is_polyline(geom) else "line"
    elif geom_type == "MultiPoint":
        return "multipoint"
    elif geom_type == "Point":
        return "points"
    else:
        raise ValueError(f"No matching napari shape for {geom_type}")


def is_rectangle(geom: Geometry) -> bool:
    """Check if a geometry is a rectangle."""
    # TODO automatically detect rectangular polygons
    if isinstance(geom, Polygon):
        ...
    return False


def is_polyline(geom: Geometry) -> bool:
    """Check if a geometry is a path/polyline."""
    return len(get_coords(geom)) > 2


def estimate_ellipse(poly: Polygon) -> np.ndarray:
    """Fit an ellipse to the polygon."""
    raise NotImplementedError


# TODO extract color
def get_properties(collection) -> dict:
    """Return properties sorted into a dataframe-like dictionary."""
    properties = defaultdict(list)
    try:
        for geom in collection:
            for k, v in geom.properties.items():
                # handles QuPath measurement storage
                # TODO move to separate function
                if k == "measurements":
                    for d in v:
                        try:
                            properties[d["name"]].append(d["value"])
                        except KeyError:
                            pass
                else:
                    properties[k].append(v)
    except AttributeError:
        return {}

    return properties
