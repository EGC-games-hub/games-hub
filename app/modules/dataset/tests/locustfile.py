from locust import HttpUser, TaskSet, task

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
    on_start = None

    def on_start(self):
        # warm-up: visit upload page to obtain CSRF if needed
        try:
            self.dataset_upload()
        except Exception:
            # keep running even if upload page is not available in this environment
            pass

    @task(3)
    def dataset_upload(self):
        """Visit dataset upload page and extract CSRF token (if present)."""
        response = self.client.get("/dataset/upload")
        # utility will raise if token not found; swallow to avoid failing the locust run
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
        # Basic health check
        if resp.status_code != 200:
            print(f"Homepage returned status {resp.status_code}")
            return

        body = resp.text or ""

        # Check for Spanish heading or fallback English
        if not ("Datasets más populares" in body or "Datasets mas populares" in body or "Most popular datasets" in body):
            # also try to find the table structure used by the template
            if not re.search(r"<table[\s\S]*class=\"table table-hover\"", body):
                print("Trending section not found on homepage (no heading or expected table).")
                return

        # Quick heuristic: count badges that indicate download counts
        badges = re.findall(r"<span class=\"badge bg-primary\">", body)
        if len(badges) == 0:
            # not fatal, but note it
            print("No primary download badges found in homepage trending section.")


class DatasetUser(HttpUser):
    tasks = [DatasetCommentsBehavior, DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
