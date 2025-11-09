import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile
from app.modules.auth.repositories import UserRepository
from flask import url_for, session
import pyotp


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    for module testing (por example, new users)
    """
    with test_client.application.app_context():
        user_test = User(email="user@example.com", password="test1234")
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


def test_2fa_setup_flow(test_client):
    login_response = test_client.post(
        "/login",
        data=dict(email="test@example.com", password="test1234"),
        follow_redirects=True
    )
    assert login_response.status_code == 200

    setup_response = test_client.get("/2fa/setup")
    assert setup_response.status_code == 200
    assert b"scan the QR code" in setup_response.data.lower()

    user = UserRepository().get_by_email("test@example.com")
    assert user.totp_secret is not None
    assert not user.two_factor_enabled  

    totp = pyotp.TOTP(user.totp_secret)
    valid_token = totp.now()

    confirm_response = test_client.post(
        "/2fa/confirm",
        data=dict(token=valid_token),
        follow_redirects=True
    )
    assert confirm_response.status_code == 200
    assert b"two-factor authentication enabled" in confirm_response.data.lower()

    user = UserRepository().get_by_email("test@example.com")
    assert user.two_factor_enabled


def test_2fa_login_flow(test_client, clean_database):
    user = User(email="2fa_test@example.com", password="test1234")
    user.totp_secret = pyotp.random_base32()
    user.two_factor_enabled = True
    db.session.add(user)
    db.session.commit()

    login_response = test_client.post(
        "/login",
        data=dict(email="2fa_test@example.com", password="test1234"),
        follow_redirects=True
    )
    assert login_response.status_code == 200
    assert b"authentication code" in login_response.data.lower()
    assert "pre_2fa_user_id" in session

    totp = pyotp.TOTP(user.totp_secret)
    valid_token = totp.now()

    verify_response = test_client.post(
        "/2fa/verify",
        data=dict(token=valid_token),
        follow_redirects=True
    )
    assert verify_response.status_code == 200
    assert verify_response.request.path == url_for("public.index")
    assert "pre_2fa_user_id" not in session


def test_2fa_verification_invalid_token(test_client, clean_database):
    user = User(email="2fa_test@example.com", password="test1234")
    user.totp_secret = pyotp.random_base32()
    user.two_factor_enabled = True
    db.session.add(user)
    db.session.commit()

    test_client.post(
        "/login",
        data=dict(email="2fa_test@example.com", password="test1234"),
        follow_redirects=True
    )

    verify_response = test_client.post(
        "/2fa/verify",
        data=dict(token="000000"),
        follow_redirects=True
    )
    assert verify_response.status_code == 200
    assert b"invalid authentication code" in verify_response.data.lower()
    assert verify_response.request.path == url_for("auth.two_factor_verify")


def test_2fa_verify_endpoint_requires_session(test_client):
    response = test_client.get("/2fa/verify", follow_redirects=True)
    assert response.request.path == url_for("auth.login")