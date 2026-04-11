import geojson
import pytest

from napari_geojson import write_shapes

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
