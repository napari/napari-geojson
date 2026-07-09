"""Tests for the writer part of the plugin."""

import warnings

import geojson
import numpy as np
import pytest

from napari_geojson._writer import (
    _close_linear_ring,
    _ellipse_to_polygon,
    _linear_ring_orientation,
    _orient_linear_ring,
    _split_rings,
    write_shapes,
)

sample_shapes = [
    ([[0, 0], [0, 5], [5, 5], [5, 0]], "ellipse", "Polygon"),
    ([[0, 0], [5, 5], [0, 10]], "polygon", "Polygon"),
    ([[0, 0], [0, 5], [5, 5], [5, 0]], "rectangle", "Polygon"),
    ([[0, 5], [5, 0]], "line", "LineString"),
    ([[0, 0], [5, 5], [0, 10]], "path", "LineString"),
]

# Closed exterior ring and hole shared by the _split_rings trailing-vertex tests.
EXTERIOR_RING = np.array([[0, 0], [3, 0], [3, 3], [0, 3], [0, 0]])
HOLE_RING = np.array([[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]])
POLYGON_WITH_HOLE = np.vstack([EXTERIOR_RING, HOLE_RING])


def test_write_shapes_outputs_feature_collection(tmp_path):
    """Writer writes standard GeoJSON Features inside one FeatureCollection."""
    fname = tmp_path / "sample.geojson"
    layer_data = [
        (
            [np.array(shape[0]) for shape in sample_shapes],
            {"shape_type": [shape[1] for shape in sample_shapes]},
            "shapes",
        )
    ]

    write_shapes(str(fname), layer_data)

    with open(fname) as fp:
        collection = geojson.load(fp)

    assert isinstance(collection, geojson.FeatureCollection)
    actual_geom_types = [feature["geometry"]["type"] for feature in collection.features]
    expected_geom_types = [shape[2] for shape in sample_shapes]
    assert actual_geom_types == expected_geom_types

    # check that polygons written out are closed rings
    for geom in collection.features[:-2]:
        coords = np.array(list(geojson.utils.coords(geom)))
        assert np.array_equal(coords[0], coords[-1])

    # Verify GeoJSON coordinates are in XY (Z optional) order — reversed from napari ZYX
    for shape, feature in zip(sample_shapes[-2:], collection.features[-2:]):
        napari_coords = np.asarray(shape[0])
        expected = napari_coords[..., ::-1]
        actual = np.array(list(geojson.utils.coords(feature)))
        assert actual.shape == expected.shape
        assert np.array_equal(actual, expected)


def test_write_points_outputs_multipoint_feature(tmp_path):
    """Test a napari Points layer written as a GeoJSON MultiPoint feature."""
    fname = tmp_path / "points.geojson"
    points = np.array([[2, 1], [1, 2]])
    layer_data = [(points, {}, "points")]

    write_shapes(str(fname), layer_data)

    with open(fname) as fp:
        collection = geojson.load(fp)

    assert isinstance(collection, geojson.FeatureCollection)
    assert len(collection.features) == 1
    feature = collection.features[0]
    assert feature["geometry"]["type"] == "MultiPoint"
    np.testing.assert_array_equal(
        np.asarray(feature["geometry"]["coordinates"]),
        points[..., ::-1],
    )


def test_write_ellipse_outputs_single_xy_ring(tmp_path):
    """Ellipse writes one linear ring in GeoJSON XY order.

    Uses an asymmetric bounding box so XY differs from napari's YX order.
    """
    fname = tmp_path / "ellipse.geojson"
    # napari YX bounding box: axis0 (rows) span 0-10, axis1 (cols) span 0-4
    ellipse = np.array([[0, 0], [0, 4], [10, 4], [10, 0]])
    layer_data = [([ellipse], {"shape_type": ["ellipse"]}, "shapes")]

    write_shapes(str(fname), layer_data)

    with open(fname) as fp:
        collection = geojson.load(fp)

    coordinates = collection.features[0]["geometry"]["coordinates"]
    # A single linear ring, not one ring per vertex
    assert len(coordinates) == 1
    ring = np.asarray(coordinates[0])
    # Output is the ellipse polygon with napari YX reversed to GeoJSON XY
    # (atol accounts for geojson rounding coordinates on serialization).
    expected = _ellipse_to_polygon(ellipse)[:, ::-1]
    np.testing.assert_allclose(ring, expected, atol=1e-6)
    # closed ring
    np.testing.assert_array_equal(ring[0], ring[-1])


def test_write_polygon_with_hole(tmp_path):
    """Writer writes valid GeoJSON polygon with an exterior ring and interior hole per RFC 7946.

    Exterior ring should be counterclockwise and hole should be clockwise in GeoJSON XY space, regardless of the order of vertices in the napari input.
    """
    fname = tmp_path / "polygon_with_hole_oriented.geojson"
    polygon = np.array(
        [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0],
            [2, 2],
            [2, 4],
            [4, 4],
            [4, 2],
            [2, 2],
        ]
    )
    layer_data = [([polygon], {"shape_type": ["polygon"]}, "shapes")]

    write_shapes(str(fname), layer_data)

    with open(fname) as fp:
        collection = geojson.load(fp)

    exterior, hole = [
        np.asarray(ring) for ring in collection.features[0]["geometry"]["coordinates"]
    ]
    assert _linear_ring_orientation(exterior)
    assert not _linear_ring_orientation(hole)


def test_split_rings_ignores_trailing_path_terminator():
    """Split rings should ignore a final path closing vertex."""
    polygon = np.vstack([POLYGON_WITH_HOLE, [0, 0]])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        exterior, hole = _split_rings(polygon)

    assert not caught

    np.testing.assert_array_equal(exterior, EXTERIOR_RING)
    np.testing.assert_array_equal(hole, HOLE_RING)


def test_close_linear_ring_rejects_three_position_closed_ring():
    """Close ring should reject already-closed rings with only three positions."""
    ring = np.array([[0, 0], [1, 0], [0, 0]])

    with pytest.raises(ValueError, match="at least four positions"):
        _close_linear_ring(ring)


@pytest.mark.parametrize("exterior", [True, False])
def test_orient_linear_ring_orients_closed_ring(exterior):
    """Orient ring should preserve closure and apply the requested winding."""
    ring = np.array([[0, 0], [0, 1], [1, 0], [0, 0]])

    oriented = _orient_linear_ring(ring, exterior=exterior)

    np.testing.assert_array_equal(oriented[0], oriented[-1])
    assert len(oriented) == 4
    assert _linear_ring_orientation(oriented) == exterior


@pytest.mark.parametrize(
    "trailing_vertices",
    [
        np.array([[0, 4]]),
        np.array([[0, 4], [1, 5]]),
        np.array([[0, 4], [1, 5], [2, 4]]),
    ],
)
def test_split_rings_warns_and_trims_trailing_vertices(trailing_vertices):
    """Split rings should warn and trim trailing vertices after closed rings."""
    polygon = np.vstack([POLYGON_WITH_HOLE, trailing_vertices])

    with pytest.warns(UserWarning, match="Ignoring trailing polygon vertices"):
        exterior, hole = _split_rings(polygon)

    np.testing.assert_array_equal(exterior, EXTERIOR_RING)
    np.testing.assert_array_equal(hole, HOLE_RING)
