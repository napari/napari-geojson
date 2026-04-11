import numpy as np
import pytest


def test_read_feature_collection_test_data(read_test_data):
    """Reader loads valid FeatureCollection test data into points and shapes layers."""
    layer_data_list = read_test_data("valid_feature_collection.geojson")

    assert [layer[2] for layer in layer_data_list] == ["points", "shapes"]

    points, point_meta, kind = layer_data_list[0]
    assert kind == "points"
    np.testing.assert_array_equal(points, np.array([[2, 1], [4, 3]]))
    assert point_meta["properties"]["name"] == ["point-a", "point-b"]

    shapes, shape_meta, kind = layer_data_list[1]
    assert kind == "shapes"
    assert shape_meta["shape_type"] == ["line", "polygon"]
    assert shape_meta["properties"]["name"] == ["line-a", "poly-a"]
    np.testing.assert_array_equal(shapes[0], np.array([[20, 10], [40, 30]]))
    np.testing.assert_array_equal(
        shapes[1],
        np.array([[200, 100], [200, 110], [210, 110], [200, 100]]),
    )


def test_read_geometry_collection_test_data(read_test_data):
    """Reader accepts valid top-level GeometryCollection test data."""
    layer_data_list = read_test_data("valid_geometry_collection.geojson")

    assert [layer[2] for layer in layer_data_list] == ["points", "shapes"]

    points, point_meta, kind = layer_data_list[0]
    assert kind == "points"
    np.testing.assert_array_equal(points, np.array([[6, 5], [8, 7]]))
    assert point_meta["properties"] == {}

    shapes, shape_meta, kind = layer_data_list[1]
    assert kind == "shapes"
    assert shape_meta["shape_type"] == ["line", "polygon"]
    assert shape_meta["properties"] == {}
    np.testing.assert_array_equal(shapes[0], np.array([[10, 9], [12, 11]]))
    np.testing.assert_array_equal(
        shapes[1],
        np.array([[14, 13], [14, 15], [16, 15], [14, 13]]),
    )


def test_read_qupath_geojson_test_data(read_test_data):
    """Reader keeps QuPath-flavored test data readable as napari layers."""
    layer_data_list = read_test_data("qp_all_shapes.geojson")

    assert [layer[2] for layer in layer_data_list] == ["points", "points", "shapes"]

    multipoint_layer, point_layer, shapes_layer = layer_data_list

    assert multipoint_layer[1]["properties"]["object_type"] == ["annotation"]
    assert multipoint_layer[1]["properties"]["isLocked"] == [False]

    assert point_layer[1]["properties"]["object_type"] == ["annotation"]
    assert point_layer[1]["properties"]["isLocked"] == [False]

    assert shapes_layer[1]["shape_type"] == [
        "polygon",
        "polygon",
        "polygon",
        "line",
        "path",
    ]
    assert shapes_layer[1]["properties"]["object_type"] == ["annotation"] * 5
    assert shapes_layer[1]["properties"]["isLocked"] == [False] * 5


def test_read_3d_coordinates_reverse_axis_order(read_test_data):
    """Reader reverses GeoJSON XYZ test data coordinates into napari ZYX order."""
    layer_data_list = read_test_data("xyz_feature_collection.geojson")

    assert [layer[2] for layer in layer_data_list] == ["points", "shapes"]

    points, _, _ = layer_data_list[0]
    np.testing.assert_array_equal(points, np.array([[30, 20, 10], [31, 21, 11]]))

    shapes, shape_meta, _ = layer_data_list[1]
    assert shape_meta["shape_type"] == ["line", "polygon"]
    np.testing.assert_array_equal(
        shapes[0],
        np.array([[40, 30, 20], [41, 31, 21]]),
    )
    np.testing.assert_array_equal(
        shapes[1],
        np.array(
            [
                [60, 50, 40],
                [60, 50, 41],
                [61, 51, 41],
                [60, 50, 40],
            ]
        ),
    )


def test_polygon_with_hole_preserves_ring_structure(read_test_data):
    """Reader should preserve rings in polygon-with-hole test data."""
    layer_data_list = read_test_data("polygon_with_hole.geojson")

    assert [layer[2] for layer in layer_data_list] == ["shapes"]
    shapes, shape_meta, kind = layer_data_list[0]
    assert kind == "shapes"
    assert shape_meta["shape_type"] == ["polygon"]
    np.testing.assert_array_equal(
        shapes[0],
        np.array(
            [
                [0, 0], [0, 10], [10, 10], [10, 0], [0, 0],
                [2, 2], [4, 2], [4, 4], [2, 4], [2, 2],
            ]
        ),
    )
