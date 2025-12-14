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


class AuthUser(HttpUser):
    tasks = [SignupBehavior, LoginBehavior]
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




