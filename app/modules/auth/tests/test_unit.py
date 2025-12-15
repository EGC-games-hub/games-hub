import pytest
import pyotp
from flask import url_for

from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.profile.repositories import UserProfileRepository
from app.modules.auth.models import ROLES, DEFAULT_ROLE
from flask_login import login_user
from app.modules.auth.routes import change_user_role
from app.modules.profile.models import UserProfile
from app.modules.auth.routes import two_factor_confirm, two_factor_setup


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_login_success(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path != url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_email(test_client):
    response = test_client.post(
        "/login", data=dict(email="bademail@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_password(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="basspassword"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_signup_user_no_name(test_client):
    response = test_client.post(
        "/signup", data=dict(surname="Foo", email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert b"This field is required" in response.data, response.data


def test_signup_user_unsuccessful(test_client):
    email = "test@example.com"
    response = test_client.post(
        "/signup", data=dict(name="Test", surname="Foo", email=email, password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert f"Email {email} in use".encode("utf-8") in response.data


def test_signup_user_successful(test_client):
    response = test_client.post(
        "/signup",
        data=dict(name="Foo", surname="Example", email="foo@example.com", password="foo1234"),
        follow_redirects=True,
    )
    assert response.request.path == url_for("public.index"), "Signup was unsuccessful"


def test_service_create_with_profie_success(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "service_test@example.com", "password": "test1234"}

    AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1


def test_service_create_with_profile_fail_no_email(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "", "password": "1234"}

    with pytest.raises(ValueError, match="Email is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_service_create_with_profile_fail_no_password(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "test@example.com", "password": ""}

    with pytest.raises(ValueError, match="Password is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_roles_constants():
    # Ensure the roles list contains the expected roles and default is correct
    assert "admin" in ROLES
    assert "curator" in ROLES
    assert "standard" in ROLES
    assert "guest" in ROLES
    assert DEFAULT_ROLE == "standard"


def test_admin_can_assign_role(test_client, clean_database):
    repo = UserRepository()

    admin = repo.create(email="admin@example.com", password="adminpass", role="admin")

    user = repo.create(email="user@example.com", password="userpass")

    with test_client.application.test_request_context(f"/admin/users/{user.id}/role", method="POST", data={"role": "curator"}):
        login_user(admin)
        resp = change_user_role(user.id)

    repo.session.expire_all()
    updated = repo.get_by_id(user.id)
    assert updated.role == "curator"


def test_invalid_role_is_rejected(test_client, clean_database):
    repo = UserRepository()

    admin = repo.create(email="admin2@example.com", password="adminpass", role="admin")

    user = repo.create(email="user2@example.com", password="userpass")
    
    with test_client.application.test_request_context(f"/admin/users/{user.id}/role", method="POST", data={"role": "not-a-role"}):
        login_user(admin)
        resp = change_user_role(user.id)

    
    repo.session.expire_all()
    updated = repo.get_by_id(user.id)
    assert updated.role == "standard"

def test_2fa_setup_creates_secret_and_returns_uri(test_client, clean_database):
    repo = UserRepository()

    # create user and login
    user = repo.create(email="u2fa@example.com", password="pass1234")
    # create a minimal profile so templates that access current_user.profile render correctly
    profile = UserProfile(user_id=user.id, name="U2FA", surname="Tester")
    repo.session.add(profile)
    repo.session.commit()

    # Call the view directly inside a request context and programmatically login the user to avoid
    # relying on the test client's request lifecycle (which can detach DB instances in these tests).
    with test_client.application.test_request_context("/2fa/setup"):
        login_user(user)
        html = two_factor_setup()

    # reload user and check secret and flag
    repo.session.expire_all()
    updated = repo.get_by_id(user.id)
    assert getattr(updated, "totp_secret", None) is not None
    assert updated.two_factor_enabled is False


def test_2fa_qrcode_requires_auth_and_secret(test_client, clean_database):
    repo = UserRepository()

    # make sure client is logged out so we start unauthenticated
    test_client.get("/logout", follow_redirects=True)

    # unauthenticated -> 401
    resp = test_client.get("/2fa/qrcode")
    assert resp.status_code == 401

    # create user but don't set totp_secret
    user = repo.create(email="noqr@example.com", password="pass1234")


    # login (do not follow redirects to avoid template rendering errors when profile is missing)
    resp = test_client.post("/login", data=dict(email=user.email, password="pass1234"), follow_redirects=False)
    assert resp.status_code in (302, 303)

    # no secret -> 404
    resp = test_client.get("/2fa/qrcode")
    assert resp.status_code == 404

    # set secret and request qrcode
    user.totp_secret = pyotp.random_base32()
    repo.session.add(user)
    repo.session.commit()

    resp = test_client.get("/2fa/qrcode")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    assert len(resp.data) > 0


def test_2fa_confirm_enables_2fa_with_valid_token(test_client, clean_database):
    repo = UserRepository()

    user = repo.create(email="confirm@example.com", password="pass1234")
    # assign a known secret
    secret = pyotp.random_base32()
    user.totp_secret = secret
    repo.session.add(user)
    repo.session.commit()

    # create a minimal profile so the index/profile pages render properly after login
    profile = UserProfile(user_id=user.id, name="Confirm", surname="User")
    repo.session.add(profile)
    repo.session.commit()

    # Instead of going through the test_client (which may render templates requiring a full session/profile),
    # call the view function inside a test_request_context and programmatically login the user.
    totp = pyotp.TOTP(secret)
    token = totp.now()

    with test_client.application.test_request_context("/2fa/confirm", method="POST", data={"token": token, "submit": "Verify"}):
        # login_user binds current_user for this request context
        login_user(user)
        resp = two_factor_confirm()

    # ensure DB updated
    repo.session.expire_all()
    updated = repo.get_by_id(user.id)
    assert updated.two_factor_enabled is True


def test_2fa_verify_flow_with_valid_and_invalid_token(test_client, clean_database):
    repo = UserRepository()
    auth_service = AuthenticationService()

    user = repo.create(email="verify@example.com", password="pass1234")
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.two_factor_enabled = True
    repo.session.add(user)
    repo.session.commit()

    # Ensure client is logged out first to avoid leftover authenticated user from other tests
    test_client.get("/logout", follow_redirects=True)

    # Instead of relying on the login redirect flow, set the pre-2fa session directly
    with test_client.session_transaction() as sess:
        sess["pre_2fa_user_id"] = user.id
        sess["remember_me"] = False

    # invalid token stays on verify and shows error
    resp = test_client.post("/2fa/verify", data=dict(token="000000"), follow_redirects=True)
    assert resp.request.path == url_for("auth.two_factor_verify")

    # valid token logs in and redirects to public.index
    token = pyotp.TOTP(secret).now()
    resp = test_client.post("/2fa/verify", data=dict(token=token), follow_redirects=True)
    assert resp.request.path == url_for("public.index")