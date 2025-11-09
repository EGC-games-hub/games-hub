from types import SimpleNamespace
from app.modules.recommendations.service import get_recommended_datasets


def test_get_recommended_datasets_none():
    """Si no se pasa dataset, debe devolver lista vacía."""
    assert get_recommended_datasets(None) == []


def test_get_recommended_datasets_without_metadata():
    """Si el dataset no tiene ds_meta_data, debe devolver lista vacía."""
    fake_ds = SimpleNamespace(ds_meta_data=None)
    assert get_recommended_datasets(fake_ds) == []


def test_get_recommended_datasets_without_authors():
    """Si el dataset tiene metadatos pero sin autores, debe devolver lista vacía."""
    meta = SimpleNamespace(authors=[])
    fake_ds = SimpleNamespace(ds_meta_data=meta)
    assert get_recommended_datasets(fake_ds) == []
