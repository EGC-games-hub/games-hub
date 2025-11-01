from app.modules.recommendations.service import get_recommended_datasets
from app.modules.dataset.models import Dataset

def test_get_recommended_datasets_same_author(db_session):
    """Comprueba que el servicio devuelve datasets del mismo autor en orden correcto."""
    author_id = 123
    ds1 = Dataset(id=1, author_id=author_id, downloads=100)
    ds2 = Dataset(id=2, author_id=author_id, downloads=300)
    ds3 = Dataset(id=3, author_id=author_id, downloads=200)
    ds_other = Dataset(id=4, author_id=999, downloads=999)
    
    db_session.add_all([ds1, ds2, ds3, ds_other])
    db_session.commit()

    recs = get_recommended_datasets(ds1)

    assert len(recs) == 2
    assert recs[0].downloads >= recs[1].downloads
    assert all(r.author_id == author_id for r in recs)
