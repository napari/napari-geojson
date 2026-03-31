import geojson
import numpy as np
import pytest

from napari_geojson import napari_get_reader, write_shapes
from napari_geojson._writer import get_geometry

ellipse = [[[0, 0], [0, 5], [5, 5], [5, 0]], "ellipse", "Polygon"]
line = [[[0, 0], [5, 5]], "line", "LineString"]
polygon = [[[0, 0], [5, 5], [0, 10]], "polygon", "Polygon"]
polyline = [[[0, 0], [5, 5], [0, 10]], "path", "LineString"]
rectangle = [[[0, 0], [0, 5], [5, 5], [5, 0]], "rectangle", "Polygon"]

sample_shapes = [ellipse, line, polygon, polyline, rectangle]
sample_shapes_ids = ["ellipse", "line", "polygon", "polyline", "rectangle"]


# @pytest.mark.parametrize(
#     "coords,shape_type,expected", sample_shapes, ids=sample_shapes_ids
# )
# def test_write_each_shape(
#     make_napari_viewer, tmp_path, coords, shape_type, expected
# ):  # noqa E501
#     """Writer writes a shapes layer as GeoJSON."""
#     fname = str(tmp_path / "sample.geojson")
#     viewer = make_napari_viewer()
#     shapes_layer = viewer.add_shapes(coords, shape_type=shape_type)
#     # shape was written
#     assert len(shapes_layer.data) == 1

#     data, meta, _ = shapes_layer.as_layer_data_tuple()
#     write_shapes(fname, data, meta)

#     # read back
#     with open(fname) as fp:
#         collection = geojson.load(fp)
#         geom = collection["geometries"][0]
#         assert geom.type == expected


@pytest.mark.parametrize(
    "coords,shape_type",
    [rectangle[:2], polygon[:2]],
    ids=["rectangle", "polygon"],
)
def test_polygon_ring_is_closed(coords, shape_type):
    """Written polygons have closed rings per RFC 7946 §3.1.6."""
    geom = get_geometry(coords, shape_type, flipxy=False)
    ring = geom["coordinates"]
    assert ring[0] == ring[-1], "Polygon ring must be closed"
    assert len(ring) == len(coords) + 1


@pytest.mark.parametrize(
    "coords,shape_type",
    [rectangle[:2], polygon[:2]],
    ids=["rectangle", "polygon"],
)
def test_polygon_roundtrip(tmp_path, coords, shape_type):
    """Polygon coordinates survive a write-then-read roundtrip."""
    fname = str(tmp_path / "roundtrip.geojson")
    data = [np.array(coords)]
    meta = {"shape_type": [shape_type]}
    write_shapes(fname, [(data, meta, "shapes")])

    # GeoJSON on disk must have closed rings
    with open(fname) as f:
        raw = geojson.load(f)
    ring = raw[0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1], "Polygon ring on disk must be closed"

    # Reading back should strip the closing coordinate
    reader = napari_get_reader(fname)
    layer_data_list = reader(fname)
    shape_data = layer_data_list[-1][0]
    assert len(shape_data[0]) == len(coords)
