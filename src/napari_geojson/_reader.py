"""Read geojson files into napari."""

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import geojson
import numpy as np
from geojson.geometry import Geometry, Point, Polygon

if TYPE_CHECKING:
    import napari  # pragma: no cover


def napari_get_reader(path):
    """Get implementation of the napari_get_reader hook specification."""
    if isinstance(path, list):
        path = path[0]

    if not path.lower().endswith(".geojson"):
        return None

    return reader_function


def reader_function(path) -> List["napari.types.LayerDataTuple"]:
    """Take a path or list of paths and return a list of LayerData tuples."""
    # handle both a string and a list of strings
    paths = [path] if isinstance(path, str) else path
    layer_data_tuples = []
    for _path in paths:
        layer_data = geojson_to_napari(_path)
        layer_data_tuples.extend(layer_data)
    return layer_data_tuples


# TODO if all objects are point, load into points layer?
def geojson_to_napari(fname: str) -> List[Tuple[Any, Dict, str]]:
    """Convert geojson into napari shapes data."""
    with open(fname) as f:
        data = geojson.load(f)

    if isinstance(data, geojson.FeatureCollection):
        collection = data.features
    elif isinstance(data, geojson.GeometryCollection):
        collection = data.
    # Note: this is not valid, but it's how the reader has been working
    # TODO: validate input and output!
    elif isinstance(data, (list, tuple)):
        collection = data
    else:
        collection = [data]

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

    # create a point layer for each multipoint layer in the data
    for geom in multi_point_geoms:
        layer_data.append(create_point_layer_data([geom]))

    # all singleton points to a single layer
    if point_geoms:
        layer_data.append(create_point_layer_data(point_geoms))

    # create a shape layer for all other shape geometries
    if shape_geoms:
        shapes = [get_shape(geom) for geom in shape_geoms]
        properties = get_properties(shape_geoms)
        meta = {"shape_type": shape_types, "properties": properties}
        layer_data.append((shapes, meta, "shapes"))

    return layer_data


def get_shape(geom: Geometry) -> List:
    """Return coordinates of shapes."""
    return get_coords(geom)


def get_coords(geom: Geometry, flipxy=True) -> List:
    """Return coordinates for geojson shapes."""
    coords = np.array(list(geojson.utils.coords(geom)))
    if flipxy:
        coords = np.flip(coords, 1)
    return coords


def create_point_layer_data(collection) -> Tuple[Any, Dict, str]:
    pts = np.squeeze([get_shape(geom) for geom in collection])
    pt_properties = get_properties(collection)
    pt_meta = {"properties": pt_properties}
    return (pts, pt_meta, "points")


def get_shape_type(geom: Geometry) -> str:
    """Translate geojson to napari shape notation."""
    # QuPath stores 'type' under 'geometry'
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
