from locust import HttpUser, TaskSet, task
import os

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token


class DatasetBehavior(TaskSet):
    def on_start(self):
        # Ensure we are logged in before attempting upload
        self.login()

    def login(self):
        response = self.client.get("/login")
        try:
            csrf_token = get_csrf_token(response)
        except Exception:
            csrf_token = None

        login_data = {"email": "user2@example.com", "password": "1234"}
        if csrf_token:
            login_data["csrf_token"] = csrf_token

        resp = self.client.post(
            "/login",
            data=login_data,
            name="POST /login (user)",
        )
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code}")

    @task
    def upload_dataset(self):
        # Load CSV upload page to obtain CSRF token (form) and ensure page is accessible
        response = self.client.get("/csvdataset/upload")
        try:
            csrf_token = get_csrf_token(response)
        except Exception:
            csrf_token = None

        # Locate the example CSV shipped with the repo
        csv_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "dataset_csv",
                "csv_example",
                "topselling_steam_games.csv",
            )
        )

        if not os.path.exists(csv_path):
            print(f"CSV example not found at {csv_path}")
            return

        data = {}
        if csrf_token:
            data["csrf_token"] = csrf_token

        # Open the CSV file as binary and upload to the CSV-specific endpoint
        with open(csv_path, "rb") as fh:
            files = {"file": (os.path.basename(csv_path), fh, "text/csv")}

            resp = self.client.post(
                "/csvdataset/file/upload",
                files=files,
                data=data,
                name="POST /csvdataset/file/upload",
                allow_redirects=True,
            )

        if resp.status_code not in (200, 201):
            print(f"CSV upload failed: {resp.status_code} - {resp.text[:200]}")
        else:
            try:
                json_data = resp.json()
                msg = json_data.get("message")
                if msg:
                    print(f"CSV upload response: {msg}")
            except Exception:
                pass


class DatasetUser(HttpUser):
    tasks = [DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
