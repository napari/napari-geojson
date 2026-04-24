"""A module to write geojson files from napari shapes layers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import geojson
import numpy as np
from geojson.geometry import LineString, MultiPoint, Polygon
from napari.layers.shapes._shapes_models import Ellipse

if TYPE_CHECKING:
    from napari.types import FullLayerData
    from numpy.typing import ArrayLike


def write_shapes(path: str, layer_data: list[FullLayerData]) -> str:
    """Write a single geojson file from napari shape and point layer data."""
    with open(path, "w") as fp:
        features = []
        for layer in layer_data:
            data, meta, kind = layer
            if kind == "points":
                points = np.atleast_2d(reverse_axis_order(data)).tolist()
                features.append(
                    geojson.Feature(geometry=MultiPoint(points), properties={})
                )
            else:
                features.extend(
                    [
                        geojson.Feature(geometry=get_geometry(s, t), properties={})
                        for s, t in zip(data, meta["shape_type"])  # noqa E501
                    ]
                )

        geojson.dump(geojson.FeatureCollection(features), fp)
        return fp.name


def reverse_axis_order(coords: ArrayLike) -> np.ndarray:
    """Reverse coordinate axis order along the last dimension.

    Ensures that napari ZYX order is converted to GeoJSON XY(Z optional)
    order.
    """
    return np.asarray(coords)[..., ::-1]


def get_geometry(coords: ArrayLike, shape_type: str) -> Polygon | LineString:
    """Convert napari coordinates to a GeoJSON geometry."""
    if shape_type in ["rectangle", "polygon"]:
        # Close the ring per GeoJSON spec (RFC 7946 §3.1.6)
        if not np.array_equal(coords[0], coords[-1]):
            coords = np.vstack([coords, coords[0]])
    if shape_type == "ellipse":
        coords = ellipse_to_polygon(coords)

    coords = reverse_axis_order(coords).tolist()

    if shape_type in ["rectangle", "polygon", "ellipse"]:
        return Polygon([coords])
    if shape_type in ["line", "path"]:
        return LineString(coords)
    raise ValueError(f"Shape type `{shape_type}` not supported.")


def ellipse_to_polygon(coords: ArrayLike) -> np.ndarray:
    """Convert an ellipse to a polygon."""
    # TODO implement custom function
    # Hacky way to use napari's internal conversion
    return Ellipse(np.asarray(coords))._edge_vertices
