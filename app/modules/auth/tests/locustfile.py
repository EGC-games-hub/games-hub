from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token


class SignupBehavior(TaskSet):
    def on_start(self):
        self.signup()

    @task
    def signup(self):
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/signup", data={"email": fake.email(), "password": fake.password(), "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Signup failed: {response.status_code}")


class LoginBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.login()

    @task
    def ensure_logged_out(self):
        response = self.client.get("/logout")
        if response.status_code != 200:
            print(f"Logout failed or no active session: {response.status_code}")

    @task
    def login(self):
        response = self.client.get("/login")
        if response.status_code != 200 or "Login" not in response.text:
            print("Already logged in or unexpected response, redirecting to logout")
            self.ensure_logged_out()
            response = self.client.get("/login")

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token},
            name="POST /login (user)",
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")





class TwoFactorBehavior(TaskSet):
    """
    This behavior attempts to login with a user that has 2FA enabled and
    reaches the 2FA verification page (without submitting the 2FA code).
    """

    def on_start(self):
        # ensure no active session
        self.client.get("/logout")

    @task
    def reach_2fa_prompt(self):
        # GET login page to obtain csrf token
        resp = self.client.get("/login")
        try:
            csrf_token = get_csrf_token(resp)
        except Exception:
            print("Could not extract CSRF token from login page")
            return

        # Credentials used in unit tests for 2FA flows
        data = {"email": "verify@example.com", "password": "pass1234", "csrf_token": csrf_token}

        post_resp = self.client.post("/login", data=data, allow_redirects=False)

        # If the app responds with a redirect to the 2fa verify endpoint, follow it
        location = post_resp.headers.get("Location", "") if post_resp is not None else ""
        if post_resp is not None and post_resp.status_code in (301, 302, 303) and "/2fa/verify" in location:
            verify_resp = self.client.get("/2fa/verify")
            if "Two-Factor Authentication" in verify_resp.text:
                # reached 2FA screen
                return
            else:
                print("Reached /2fa/verify but expected text not found")
                return

        # If no redirect, maybe the POST returned the 2FA page directly
        try:
            text = post_resp.text or ""
        except Exception:
            text = ""

        if "Two-Factor Authentication" in text or "/2fa/verify" in getattr(post_resp, "url", ""):
            # already on the 2FA page
            return

        # As a fallback, explicitly request the verify page and check session
        fallback = self.client.get("/2fa/verify")
        if fallback.status_code == 200 and "Two-Factor Authentication" in fallback.text:
            return
        print("Did not reach 2FA verification page after login attempt")


class AuthUser(HttpUser):
    tasks = [SignupBehavior, LoginBehavior, TwoFactorBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()


class ChangeRoleBehavior(TaskSet):

    def on_start(self):
        self.admin_login()

    def admin_login(self):
        # 1️⃣ GET login
        response = self.client.get("/login")

        # 2️⃣ POST login
        login_resp = self.client.post(
            "/login",
            data={
                "email": "admin@example.com",
                "password": "1234",
            },
            name="POST /login (admin)",
            allow_redirects=True,
        )

        if login_resp.status_code != 200:
            print(f"Admin login failed: {login_resp.status_code}")

    @task
    def change_user_role(self):
        # 3️⃣ GET admin users (para CSRF)
        users_page = self.client.get("/admin/users")
        if users_page.status_code != 200:
            print(f"Failed to load admin users page: {users_page.status_code}")
            return

        # 4️⃣ POST cambio de rol
        resp = self.client.post(
            "/admin/users/1/role",
            data={
                "role": "curator",
            },
            name="/admin/users/<id>/role",
        )

        if resp.status_code != 200:
            print(f"Role change failed: {resp.status_code}")

class AdminUser(HttpUser):
    tasks = [ChangeRoleBehavior]
    min_wait = 3000
    max_wait = 6000
    host = get_host_for_locust_testing()
