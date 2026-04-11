"""Shared pytest test data helpers for GeoJSON reader tests."""

from pathlib import Path

import pytest

from napari_geojson import napari_get_reader


@pytest.fixture
def test_data_dir() -> Path:
    """Return the root directory holding test data files."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def read_test_data(test_data_dir: Path):
    """Return a helper that reads test data through the napari reader contribution."""

    def _read_test_data(name: str):
        path = test_data_dir / name
        reader = napari_get_reader(str(path))
        assert callable(reader)
        return reader(str(path))

    return _read_test_data
