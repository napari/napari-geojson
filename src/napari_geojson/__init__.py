"""GeoJSON reader and writer packages for napari."""

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"


from ._reader import napari_get_reader
from ._writer import write_shapes

__all__ = ["napari_get_reader", "write_shapes"]
