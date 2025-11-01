from app.modules.dataset.models import Dataset

def get_recommended_datasets(dataset):
    """Devuelve datasets del mismo autor, ordenados por descargas (máx. 5)."""
    if not dataset or not getattr(dataset, "author_id", None):
        return []
    
    return (
        Dataset.query
        .filter(Dataset.author_id == dataset.author_id, Dataset.id != dataset.id)
        .order_by(Dataset.downloads.desc())
        .limit(5)
        .all()
    )
