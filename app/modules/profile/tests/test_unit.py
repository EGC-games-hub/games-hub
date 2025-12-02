import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile
from app.modules.auth.repositories import UserRepository
from flask import url_for, session
import pyotp
from datetime import datetime, timedelta

from app.modules.dataset.models import DSMetaData, DataSet, PublicationType


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    for module testing (por example, new users)
    """
    with test_client.application.app_context():
        user_test = User(email="user@example.com")
        user_test.set_password("test1234")
        db.session.add(user_test)
        db.session.commit()

        profile = UserProfile(user_id=user_test.id, name="Name", surname="Surname")
        db.session.add(profile)
        db.session.commit()

    yield test_client


def test_edit_profile_page_get(test_client):
    """
    Tests access to the profile editing page via a GET request.
    """
    login_response = login(test_client, "user@example.com", "test1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    response = test_client.get("/profile/edit")
    assert response.status_code == 200, "The profile editing page could not be accessed."
    assert b"Edit profile" in response.data, "The expected content is not present on the page"

    logout(test_client)

def test_2fa_setup_requires_auth(test_client):
    response = test_client.get("/2fa/setup", follow_redirects=True)
    assert response.request.path == url_for("auth.login")


# ------------------------------
# Tests for 'view user profile' feature
# ------------------------------

def test_public_profile_existing_user_returns_200_and_shows_profile(test_client):
    """GET /profile/<id> for an existing user with profile should return 200 and render basic info."""
    # Find the user created in the module fixture
    with test_client.application.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None and user.profile is not None
        user_id = user.id

    resp = test_client.get(f"/profile/{user_id}")
    assert resp.status_code == 200
    # Basic template markers and profile fields
    assert b"User profile" in resp.data
    assert b"Profile Information" in resp.data
    assert b"Name" in resp.data
    assert b"Surname" in resp.data


def test_public_profile_is_accessible_without_login(test_client):
    """Public profile must be accessible without authentication (no redirect to login)."""
    with test_client.application.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None and user.profile is not None
        user_id = user.id

    resp = test_client.get(f"/profile/{user_id}", follow_redirects=False)
    # No redirect to /login — should be a direct 200
    assert resp.status_code == 200


def test_public_profile_nonexistent_user_returns_404(test_client):
    """GET /profile/<id> for a non-existent user should return 404."""
    resp = test_client.get("/profile/999999")
    assert resp.status_code == 404


def test_public_profile_user_without_profile_returns_404(test_client):
    """GET /profile/<id> for a user without profile should return 404."""
    with test_client.application.app_context():
        u = User(email="no_profile@example.com")
        u.set_password("secret1234")
        db.session.add(u)
        db.session.commit()
        user_id = u.id

    resp = test_client.get(f"/profile/{user_id}")
    assert resp.status_code == 404


def test_public_profile_hides_sensitive_email(test_client):
    """Ensure public profile page doesn't leak user's email address."""
    with test_client.application.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None and user.profile is not None
        email = user.email.encode()

    resp = test_client.get(f"/profile/{user.id}")
    assert resp.status_code == 200
    assert email not in resp.data


def test_public_profile_shows_no_datasets_message_when_empty(test_client):
    """For user with no datasets, the page should show the 'No datasets found' message."""
    with test_client.application.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None and user.profile is not None

        # Ensure user has no datasets
        DataSet.query.filter_by(user_id=user.id).delete()
        db.session.commit()

        user_id = user.id

    resp = test_client.get(f"/profile/{user_id}")
    assert resp.status_code == 200
    assert b"No datasets found" in resp.data


def _make_dataset_for_user(user_id: int, title: str, created_at: datetime):
    meta = DSMetaData(
        title=title,
        description="desc",
        publication_type=PublicationType.OTHER,
        tags="",
    )
    db.session.add(meta)
    db.session.flush()

    ds = DataSet(user_id=user_id, ds_meta_data_id=meta.id, created_at=created_at)
    db.session.add(ds)
    db.session.commit()
    return ds
