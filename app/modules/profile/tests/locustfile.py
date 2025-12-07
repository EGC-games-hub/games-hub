from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing


class ViewPublicProfileBehavior(TaskSet):
    @task
    def view_seeded_user_profile(self):
        # Seeders create user1 and user2; profiles are public at /profile/<id>
        # Try user 2's profile to avoid hitting the logged-in user
        response = self.client.get("/profile/2")
        if response.status_code != 200:
            # Fallback: try user 1
            response = self.client.get("/profile/1")
        if response.status_code != 200:
            print(f"Public profile view failed: {response.status_code}")

    @task
    def view_profile_pagination(self):
        # Exercise pagination on the public profile, if datasets exist
        # Use ?page=2 against user 2; fallback to page=1
        resp = self.client.get("/profile/2?page=2")
        if resp.status_code == 404:
            # Fallback to first page
            resp = self.client.get("/profile/2?page=1")
        if resp.status_code != 200:
            print(f"Public profile pagination failed: {resp.status_code}")


class AnonymousUser(HttpUser):
    tasks = [ViewPublicProfileBehavior]
    min_wait = 3000
    max_wait = 6000
    host = get_host_for_locust_testing()
