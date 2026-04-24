"""Tests for the writer part of the plugin."""

import geojson
import numpy as np

from napari_geojson._writer import write_shapes

sample_shapes = [
    ([[0, 0], [0, 5], [5, 5], [5, 0]], "ellipse", "Polygon"),
    ([[0, 0], [5, 5], [0, 10]], "polygon", "Polygon"),
    ([[0, 0], [0, 5], [5, 5], [5, 0]], "rectangle", "Polygon"),
    ([[0, 0], [5, 5]], "line", "LineString"),
    ([[0, 0], [5, 5], [0, 10]], "path", "LineString"),
]


def test_write_shapes_outputs_feature_collection(tmp_path):
    """Writer writes all shapes as a single GeoJSON FeatureCollection."""
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
