"""A module to write geojson files from napari shapes layers."""

from __future__ import annotations

import warnings
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
                points = np.atleast_2d(_reverse_axis_order(data)).tolist()
                features.append(
                    geojson.Feature(geometry=MultiPoint(points), properties={})
                )
            else:
                features.extend(
                    [
                        geojson.Feature(geometry=_get_geometry(s, t), properties={})
                        for s, t in zip(data, meta["shape_type"])
                    ]
                )

        geojson.dump(geojson.FeatureCollection(features), fp)
        return fp.name


def _reverse_axis_order(coords: ArrayLike) -> np.ndarray:
    """Reverse coordinate axis order along the last dimension.

    Ensures that napari (Z)YX order is converted to GeoJSON XY(Z optional)
    order.
    """
    return np.asarray(coords)[..., ::-1]


def _get_geometry(coords: ArrayLike, shape_type: str) -> Polygon | LineString:
    """Convert napari coordinates to a GeoJSON geometry."""
    if shape_type == "ellipse":
        # Ellipse handling will be reworked, see #21
        coords = _ellipse_to_polygon(coords)
        return Polygon([_reverse_axis_order(coords).tolist()])

    if shape_type in ["rectangle", "polygon"]:
        return Polygon([ring.tolist() for ring in _get_polygon_rings(coords)])

    coords = _reverse_axis_order(coords).tolist()

    if shape_type in ["line", "path"]:
        return LineString(coords)
    raise ValueError(f"Shape type `{shape_type}` not supported.")


def _get_polygon_rings(coords: ArrayLike) -> list[np.ndarray]:
    """Convert flat napari polygon vertices into oriented GeoJSON linear rings.

    Converts the flat vertex array to XY order, splits it into rings, and
    orients them per RFC 7946: exterior ring first, then any holes.
    """
    coords = _reverse_axis_order(np.atleast_2d(coords))
    return [
        _orient_linear_ring(ring, exterior=index == 0)
        for index, ring in enumerate(_split_rings(coords))
    ]


def _split_rings(coords: np.ndarray) -> list[np.ndarray]:
    """Split a flat vertex array into individual closed linear rings.

    napari stores polygons with holes as a flat list of vertices where each
    closed ring repeats its first vertex.
    If no ring terminator is present, the full array is treated as a single ring.
    After a series of rings, an optional path terminator may be present, but is
    silently trimmed.
    Any other trailing vertices are trimmed with a warning because they do not define a
    valid ring and result in bizarre output that is also not valid GeoJSON. See:
    https://github.com/napari/napari/issues/9013
    """
    rings = []
    start = 0
    for end in range(1, len(coords)):
        if end - start >= 3 and np.array_equal(coords[end], coords[start]):
            rings.append(_close_linear_ring(coords[start : end + 1]))
            start = end + 1

    remainder = coords[start:]
    # all rings closed
    if len(remainder) == 0:
        return rings
    # no closed rings, so treat as single ring and close it
    if not rings:
        return [_close_linear_ring(remainder)]
    # path-closing vertex present, silently ignore it
    if len(remainder) == 1 and np.array_equal(remainder[0], rings[0][0]):
        return rings
    # Extra invalid vertices present
    warnings.warn(
        (
            "Ignoring trailing polygon vertices after closed rings because "
            "they do not form a valid GeoJSON linear ring."
        ),
        UserWarning,
        stacklevel=2,
    )
    return rings


def _close_linear_ring(coords: np.ndarray) -> np.ndarray:
    """Return a valid GeoJSON linear ring, closing it if needed."""
    coords = np.asarray(coords)
    if not np.array_equal(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[0]])
    # A valid ring needs at least three distinct vertices plus the closing
    # repeat of the first, i.e. four positions (RFC 7946 §3.1.6).
    if len(coords) < 4:
        raise ValueError("GeoJSON linear rings require at least four positions.")
    return coords


def _orient_linear_ring(coords: np.ndarray, exterior: bool) -> np.ndarray:
    """Orient a valid GeoJSON linear ring per RFC 7946 §3.1.6.

    In GeoJSON, the exterior ring of a polygon must be counterclockwise
    and holes must be clockwise.
    """
    orientation = _linear_ring_orientation(coords)
    return coords if orientation == exterior else coords[::-1]


def _linear_ring_orientation(coords: np.ndarray) -> bool:
    """Return the orientation of a closed linear ring in GeoJSON XY space.

    Uses the shoelace formula to compute the signed area:
    - True (positive signed area) indicates counterclockwise orientation (exterior ring in GeoJSON)
    - False (negative signed area) indicates clockwise orientation (hole in GeoJSON)
    """
    coords = np.atleast_2d(np.asarray(coords, dtype=float))
    if coords.shape[1] < 2:
        raise ValueError("Polygon coordinates must have at least two dimensions.")

    x, next_x = coords[:-1, 0], coords[1:, 0]
    y, next_y = coords[:-1, 1], coords[1:, 1]
    signed_area = float(0.5 * np.sum(x * next_y - next_x * y))

    return signed_area > 0


def _ellipse_to_polygon(coords: ArrayLike) -> np.ndarray:
    """Convert an ellipse to a polygon."""
    # TODO implement custom function
    # Hacky way to use napari's internal conversion
    return Ellipse(np.asarray(coords))._edge_vertices
