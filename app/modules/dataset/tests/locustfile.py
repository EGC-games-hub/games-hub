from locust import HttpUser, TaskSet, task
import os

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token
from bs4 import BeautifulSoup
import re
import time


class DatasetCommentsBehavior(TaskSet):
    """Locust tasks to exercise comments on datasets:
    - login as test user
    - find a dataset id from /dataset/list
    - view dataset page
    - post a comment (JSON)
    - verify comment appears and attempt to delete it
    """

    def on_start(self):
        self.ensure_logged_out()
        self.login()
        self.find_dataset()

    def ensure_logged_out(self):
        # best-effort logout
        try:
            self.client.get("/logout")
        except Exception:
            pass

    def login(self):
        response = self.client.get("/login")
        # reuse existing helper to extract CSRF token (login form uses WTForms)
        try:
            csrf_token = get_csrf_token(response)
        except Exception:
            csrf_token = None

        data = {"email": "user1@example.com", "password": "1234"}
        if csrf_token:
            data["csrf_token"] = csrf_token

        response = self.client.post("/login", data=data)
        if response.status_code != 200:
            print(f"Login may have failed: {response.status_code}")

    def find_dataset(self):
        """Attempt to find an unsynchronized dataset id from the list page.
        Falls back to dataset id 1 if nothing found.
        """
        resp = self.client.get("/dataset/list")
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            link = soup.find("a", href=re.compile(r"^/dataset/unsynchronized/"))
            if link:
                m = re.search(r"/dataset/unsynchronized/(\d+)/", link.get("href", ""))
                if m:
                    self.dataset_id = int(m.group(1))
                    return

            # fallback: try to parse any download link (/dataset/download/<id>)
            link = soup.find("a", href=re.compile(r"^/dataset/download/\d+"))
            if link:
                m = re.search(r"/dataset/download/(\d+)", link.get("href", ""))
                if m:
                    self.dataset_id = int(m.group(1))
                    return
        except Exception:
            pass

        # final fallback
        self.dataset_id = 1

    @task(3)
    def view_dataset(self):
        self.client.get(f"/dataset/unsynchronized/{self.dataset_id}/")

    @task(7)
    def post_comment(self):
        # Compose a unique comment
        comment_text = f"Locust comment {int(time.time())} - {fake.sentence(nb_words=6)}"

        # Post as JSON to avoid CSRF issues in forms
        resp = self.client.post(f"/dataset/{self.dataset_id}/comments", json={"content": comment_text}, allow_redirects=False)

        # Fetch the dataset page and try to find the posted comment; if found, try to delete it
        view = self.client.get(f"/dataset/unsynchronized/{self.dataset_id}/")
        try:
            soup = BeautifulSoup(view.text, "html.parser")
            # comments are in <p>{{ comment.content }}</p>
            comment_p = soup.find("p", string=re.compile(re.escape(comment_text)))
            if comment_p:
                # The delete form is placed near the comment; search previous forms with moderate action
                form = comment_p.find_previous("form", action=re.compile(r"/dataset/\d+/comments/\d+/moderate"))
                if form:
                    action = form.get("action")
                    # send delete action
                    self.client.post(action, data={"action": "delete"}, allow_redirects=False)
        except Exception:
            # don't fail the locust worker on parsing errors
            pass


class DatasetBehavior(TaskSet):
    """Merged behavior: homepage checks, upload warm-up and CSV upload with login.

    Combines the previous two DatasetBehavior classes so a single TaskSet runs all
    relevant dataset-related tasks.
    """

    def on_start(self):
        # Best-effort: ensure logged out then login, then warm-up upload page
        try:
            self.ensure_logged_out()
        except Exception:
            pass

        try:
            self.login()
        except Exception:
            pass

        try:
            # warm-up: visit upload page to obtain CSRF if needed
            self.dataset_upload()
        except Exception:
            pass

    def ensure_logged_out(self):
        try:
            self.client.get("/logout")
        except Exception:
            pass

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

    @task(3)
    def dataset_upload(self):
        """Visit dataset upload page and extract CSRF token (if present)."""
        response = self.client.get("/dataset/upload")
        try:
            get_csrf_token(response)
        except Exception:
            pass

    @task(5)
    def homepage_trending_check(self):
        """Hit homepage and assert trending section exists and contains expected structure.

        Locust tasks should be resilient: don't raise on minor mismatches, but log them.
        """
        resp = self.client.get("/")
        if resp.status_code != 200:
            print(f"Homepage returned status {resp.status_code}")
            return

        body = resp.text or ""

        # Check for Spanish heading or fallback English
        if not (
            "Datasets más populares" in body
            or "Datasets mas populares" in body
            or "Most popular datasets" in body
        ):
            if not re.search(r"<table[\s\S]*class=\"table table-hover\"", body):
                print("Trending section not found on homepage (no heading or expected table).")
                return

        badges = re.findall(r"<span class=\"badge bg-primary\">", body)
        if len(badges) == 0:
            print("No primary download badges found in homepage trending section.")

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
    tasks = [DatasetCommentsBehavior, DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
