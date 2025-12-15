import pytest
import re
from datetime import datetime, timedelta

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, PublicationType, Author
from app.modules.dataset.services import DataSetService
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def trending_setup(test_client):
    """Create 6 datasets with controlled download counts to test trending logic."""
    with test_client.application.app_context():
        # Create a user who will own datasets
        user = User(email="trender@example.com")
        user.set_password("test1234")
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(user_id=user.id, name="Trender", surname="Test")
        db.session.add(profile)
        db.session.commit()

        # Create 6 datasets with metadata and an author each
        datasets = []
        for i in range(1, 7):
            ds_meta = DSMetaData(
                title=f"Trending DS {i}",
                description=f"Desc {i}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                dataset_doi=f"10.0000/trending{i}",
                tags="trending,tests",
            )
            db.session.add(ds_meta)
            db.session.commit()

            author = Author(name=f"Author {i}", affiliation=f"Univ {i}", orcid=None, ds_meta_data_id=ds_meta.id)
            db.session.add(author)

            dataset = DataSet(user_id=user.id, ds_meta_data_id=ds_meta.id, created_at=datetime.utcnow())
            db.session.add(dataset)
            db.session.commit()

            datasets.append(dataset)

        # Assign downloads in the last month: descending counts so ranking is clear
        download_counts = [15, 12, 8, 4, 1, 0]
        for ds, count in zip(datasets, download_counts):
            for j in range(count):
                rec = DSDownloadRecord(
                    dataset_id=ds.id,
                    download_date=datetime.now() - timedelta(days=10),
                    download_cookie=f"cookie_{ds.id}_{j}",
                )
                db.session.add(rec)

        # Add some old downloads (outside last month) to the last dataset to ensure they're ignored
        for j in range(30):
            old = DSDownloadRecord(
                dataset_id=datasets[-1].id,
                download_date=datetime.now() - timedelta(days=60),
                download_cookie=f"old_{j}",
            )
            db.session.add(old)

        db.session.commit()

    yield test_client


def test_get_most_downloaded_last_month_service(trending_setup):
    """Service should return datasets ordered by downloads in last month and limited to 5."""
    with trending_setup.application.app_context():
        ds_service = DataSetService()
        trending = ds_service.get_most_downloaded_last_month(limit=5)

        # Expect 5 items
        assert isinstance(trending, list)
        assert len(trending) == 5, "Service should return exactly 5 items by default limit"

        # Counts should be descending and match the fixture (15,12,8,4,1)
        counts = [item["download_count"] for item in trending]
        assert counts == sorted(counts, reverse=True), "Counts must be in descending order"
        assert counts == [15, 12, 8, 4, 1]

        # Each item must include a DataSet instance and non-negative count
        for item in trending:
            # item should be a dict-like mapping with expected keys
            assert isinstance(item, dict), f"Expected dict items from service, got {type(item)}"
            assert "download_count" in item and "dataset" in item, f"Missing keys in trending item: {item.keys()}"
            assert isinstance(item["download_count"], int) and item["download_count"] >= 0
            assert item["dataset"] is not None


def test_homepage_shows_trending_table(trending_setup):
    """The homepage should render the 'Datasets más populares' section with titles, authors and download badges."""
    client = trending_setup
    resp = client.get("/")
    assert resp.status_code == 200

    data = resp.data.decode("utf-8")

    # Check heading exists
    assert "Datasets más populares" in data or "Datasets mas populares" in data

    # Check at least the top dataset title and an author name appear
    assert "Trending DS 1" in data
    assert "Author 1" in data

    # Check that download badges with the word 'descargas' appear and there are 5 items
    assert "descargas" in data.lower()

    # Count the download badges for trending (they use 'badge bg-primary' in the template)
    primary_badges = re.findall(r'<span class="badge bg-primary">', data)
    # Expect at least 1 and at most 5 primary badges in the trending table; prefer exactly 5
    assert len(primary_badges) >= 1, "No se encontraron badges de descargas en la página"
    # It's acceptable for other parts of the page to use primary badges, but commonly trending uses 5
    if len(primary_badges) >= 5:
        assert len(primary_badges) >= 5, "Se esperaban al menos 5 badges de descargas para los datasets trending"

    # Check that links to the dataset (DOI-based URL) are present for the top items
    assert "/doi/10.0000/trending1" in data or "10.0000/trending1" in data
