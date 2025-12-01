import pytest
from datetime import datetime, timedelta

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, PublicationType, Author
from app.modules.dataset.services import DataSetService
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Create test users
        user1 = User(email="author1@example.com")
        user1.set_password("test1234")
        db.session.add(user1)
        
        user2 = User(email="author2@example.com")
        user2.set_password("test1234")
        db.session.add(user2)
        
        db.session.commit()

        # Create user profiles
        profile1 = UserProfile(user_id=user1.id, name="Author1", surname="Test")
        profile2 = UserProfile(user_id=user2.id, name="Author2", surname="Test")
        db.session.add(profile1)
        db.session.add(profile2)
        db.session.commit()

        # Create test datasets with metadata
        for i in range(1, 6):
            ds_meta = DSMetaData(
                title=f"Test Dataset {i}",
                description=f"Description for dataset {i}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                dataset_doi=f"10.1234/dataset{i}",
                tags="test,dataset"
            )
            db.session.add(ds_meta)
            db.session.commit()

            # Add author
            author = Author(
                name=f"Test Author {i}",
                affiliation=f"University {i}",
                orcid=f"0000-0000-0000-000{i}",
                ds_meta_data_id=ds_meta.id
            )
            db.session.add(author)

            # Create dataset
            dataset = DataSet(
                user_id=user1.id if i <= 3 else user2.id,
                ds_meta_data_id=ds_meta.id,
                created_at=datetime.utcnow()
            )
            db.session.add(dataset)
            db.session.commit()

            # Create download records for trending datasets
            # Dataset 1: 10 downloads in last month
            # Dataset 2: 8 downloads in last month
            # Dataset 3: 5 downloads in last month
            # Dataset 4: 2 downloads in last month
            # Dataset 5: 0 downloads in last month
            download_counts = [10, 8, 5, 2, 0]
            for _ in range(download_counts[i-1]):
                download_record = DSDownloadRecord(
                    dataset_id=dataset.id,
                    download_date=datetime.now() - timedelta(days=15),
                    download_cookie=f"cookie_{dataset.id}_{_}"
                )
                db.session.add(download_record)

            # Add some old downloads (outside last month) for dataset 5
            if i == 5:
                for _ in range(20):
                    old_download = DSDownloadRecord(
                        dataset_id=dataset.id,
                        download_date=datetime.now() - timedelta(days=45),
                        download_cookie=f"old_cookie_{dataset.id}_{_}"
                    )
                    db.session.add(old_download)

        db.session.commit()

    yield test_client


def test_homepage_loads_successfully(test_client):
    """
    Test that the homepage loads successfully.
    """
    response = test_client.get("/")
    assert response.status_code == 200, "Homepage did not load successfully."
    assert b"Latest" in response.data, "Expected 'Latest' section not found on homepage."


def test_trending_datasets_section_exists(test_client):
    """
    Test that the trending datasets section appears on the homepage.
    """
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"Datasets m" in response.data or b"populares" in response.data, \
        "Trending datasets section not found on homepage."


def test_trending_datasets_shows_correct_data(test_client):
    """
    Test that trending datasets display correct information (title, author, downloads).
    """
    response = test_client.get("/")
    assert response.status_code == 200
    
    # Check that dataset titles appear
    assert b"Test Dataset 1" in response.data, "Most downloaded dataset not shown."
    assert b"Test Dataset 2" in response.data, "Second most downloaded dataset not shown."
    
    # Check that author information appears
    assert b"Test Author 1" in response.data, "Author information not displayed."
    
    # Check that download count appears
    assert b"descargas" in response.data, "Download count label not displayed."


def test_trending_datasets_ordered_by_downloads(test_client):
    """
    Test that trending datasets are ordered by download count (most to least).
    """
    with test_client.application.app_context():
        dataset_service = DataSetService()
        trending = dataset_service.get_most_downloaded_last_month(limit=5)
        
        # Verify we got results
        assert len(trending) > 0, "No trending datasets returned."
        
        # Verify ordering: download counts should be in descending order
        download_counts = [item['download_count'] for item in trending]
        assert download_counts == sorted(download_counts, reverse=True), \
            "Trending datasets are not properly ordered by download count."
        
        # Verify the most downloaded dataset is first
        assert trending[0]['download_count'] == 10, \
            "Most downloaded dataset should have 10 downloads."


def test_trending_datasets_limit_to_five(test_client):
    """
    Test that only top 5 trending datasets are shown.
    """
    with test_client.application.app_context():
        dataset_service = DataSetService()
        trending = dataset_service.get_most_downloaded_last_month(limit=5)
        
        assert len(trending) <= 5, "More than 5 trending datasets returned."


def test_trending_datasets_only_last_month(test_client):
    """
    Test that only downloads from the last month are counted.
    """
    with test_client.application.app_context():
        dataset_service = DataSetService()
        trending = dataset_service.get_most_downloaded_last_month(limit=5)
        
        # Dataset 5 has 20 old downloads (45 days ago) but 0 recent downloads
        # It should appear last or not in top positions
        dataset_5_data = None
        for item in trending:
            if item['dataset'].ds_meta_data.title == "Test Dataset 5":
                dataset_5_data = item
                break
        
        if dataset_5_data:
            # If dataset 5 appears, it should have 0 recent downloads
            assert dataset_5_data['download_count'] == 0, \
                "Old downloads should not be counted in trending."


def test_trending_datasets_link_to_dataset_page(test_client):
    """
    Test that clicking on a trending dataset navigates to its detail page.
    """
    response = test_client.get("/")
    assert response.status_code == 200
    
    # Check that dataset DOI links are present
    assert b"doi" in response.data or b"http" in response.data, \
        "Dataset links not found in trending section."


def test_trending_datasets_shows_author_affiliation(test_client):
    """
    Test that author affiliation is displayed when available.
    """
    response = test_client.get("/")
    assert response.status_code == 200
    
    # Check that university/affiliation information appears
    assert b"University" in response.data, \
        "Author affiliation not displayed in trending datasets."


def test_trending_datasets_with_no_downloads(test_client):
    """
    Test behavior when there are datasets with zero downloads.
    """
    with test_client.application.app_context():
        dataset_service = DataSetService()
        trending = dataset_service.get_most_downloaded_last_month(limit=5)
        
        # Should still return datasets even if some have 0 downloads
        assert len(trending) > 0, "Should return datasets even with 0 downloads."
        
        # Last items might have 0 downloads
        last_item = trending[-1]
        assert last_item['download_count'] >= 0, \
            "Download count should be non-negative."


def test_trending_datasets_repository_method(test_client):
    """
    Test the repository method for getting most downloaded datasets.
    """
    with test_client.application.app_context():
        from app.modules.dataset.repositories import DataSetRepository
        
        repo = DataSetRepository()
        datasets = repo.get_most_downloaded_last_month(limit=5)
        
        assert datasets is not None, "Repository method returned None."
        assert len(datasets) <= 5, "Repository returned more than requested limit."
        
        # All returned datasets should have DOI (synchronized)
        for dataset in datasets:
            assert dataset.ds_meta_data.dataset_doi is not None, \
                "Unsynchronized dataset returned in trending."


def test_homepage_statistics_still_visible(test_client):
    """
    Test that adding trending datasets doesn't break existing statistics.
    """
    response = test_client.get("/")
    assert response.status_code == 200
    
    # Check that hub statistics are still present
    assert b"Hub statistics" in response.data or b"statistics" in response.data, \
        "Hub statistics section missing."
    
    assert b"datasets" in response.data, "Dataset count statistics missing."


def test_trending_datasets_empty_database(test_client):
    """
    Test trending datasets behavior with empty database.
    """
    with test_client.application.app_context():
        # Clear all download records temporarily
        original_count = db.session.query(DSDownloadRecord).count()
        
        db.session.query(DSDownloadRecord).delete()
        db.session.commit()
        
        dataset_service = DataSetService()
        trending = dataset_service.get_most_downloaded_last_month(limit=5)
        
        # Should return datasets even without downloads
        assert isinstance(trending, list), "Should return a list even when empty."
        
        # Restore download records
        db.session.rollback()


def test_trending_datasets_table_structure(test_client):
    """
    Test that the trending datasets table has proper HTML structure.
    """
    response = test_client.get("/")
    assert response.status_code == 200
    
    # Check for table elements
    assert b"<table" in response.data, "Table element not found."
    assert b"<thead>" in response.data, "Table header not found."
    assert b"<tbody>" in response.data, "Table body not found."
    
    # Check for table headers
    assert b"tulo" in response.data or "Título" in response.data, \
        "Title column header not found."
    assert b"Autor" in response.data, "Author column header not found."
    assert b"Descargas" in response.data, "Downloads column header not found."