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
                        for s, t in zip(data, meta["shape_type"])
                    ]
                )

        geojson.dump(geojson.FeatureCollection(features), fp)
        return fp.name


def reverse_axis_order(coords: ArrayLike) -> np.ndarray:
    """Reverse coordinate axis order along the last dimension.

    Ensures that napari (Z)YX order is converted to GeoJSON XY(Z optional)
    order.
    """
    return np.asarray(coords)[..., ::-1]


def get_geometry(coords: ArrayLike, shape_type: str) -> Polygon | LineString:
    """Convert napari coordinates to a GeoJSON geometry."""
    if shape_type == "ellipse":
        coords = ellipse_to_polygon(coords)
        return Polygon(coords.tolist())

    if shape_type in ["rectangle", "polygon"]:
        return Polygon([ring.tolist() for ring in get_polygon_rings(coords)])

    coords = reverse_axis_order(coords).tolist()

    if shape_type in ["line", "path"]:
        return LineString(coords)
    raise ValueError(f"Shape type `{shape_type}` not supported.")


def get_polygon_rings(coords: ArrayLike) -> list[np.ndarray]:
    """Convert flat napari polygon vertices into GeoJSON linear rings.

    For polygons with holes, napari represents a polygon as a flat array of
    vertices where each ring is terminated by repeating the first vertex.
    GeoJSON requires separate linear rings: exterior first, then holes.
    """
    coords = np.atleast_2d(np.asarray(coords))
    rings = _split_rings(coords)
    geojson_rings = [reverse_axis_order(ring) for ring in rings]
    exterior, *holes = geojson_rings
    return [orient_linear_ring(exterior, exterior=True)] + [
        orient_linear_ring(ring, exterior=False) for ring in holes
    ]


def _split_rings(coords: np.ndarray) -> list[np.ndarray]:
    """Split a flat vertex array into individual closed linear rings."""
    rings = []
    start = 0
    for end in range(1, len(coords)):
        if end - start >= 3 and np.array_equal(coords[end], coords[start]):
            rings.append(close_linear_ring(coords[start : end + 1]))
            start = end + 1
    if start < len(coords):
        rings.append(close_linear_ring(coords[start:]))
    return rings


def close_linear_ring(coords: np.ndarray) -> np.ndarray:
    """Ensure ring is explicitly closed as per GeoJSON spec (RFC 7946 §3.1.6)."""
    if len(coords) < 3:
        raise ValueError("Polygon rings require at least three coordinates.")
    if not np.array_equal(coords[0], coords[-1]):
        coords = np.vstack([coords, coords[0]])
    return coords


def orient_linear_ring(coords: np.ndarray, exterior: bool) -> np.ndarray:
    """Orient a GeoJSON linear ring to match requirement of RFC 7946 §3.1.6.

    In GeoJSON, the exterior ring of a polygon must be counterclockwise
    and holes must be clockwise.
    """
    orientation = linear_ring_orientation(coords)

    return coords if orientation == exterior else coords[::-1]


def linear_ring_orientation(coords: np.ndarray) -> bool:
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


def ellipse_to_polygon(coords: ArrayLike) -> np.ndarray:
    """Convert an ellipse to a polygon."""
    # TODO implement custom function
    # Hacky way to use napari's internal conversion
    return Ellipse(np.asarray(coords))._edge_vertices
