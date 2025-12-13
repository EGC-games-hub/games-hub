from locust import HttpUser, task, between
import os

DOI_PATH = os.getenv("TEST_DOI_PATH", "10.1234/dataset4")

class DatasetViewUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_dataset_by_doi(self):
        with self.client.get(
            f"/doi/{DOI_PATH}/",
            name="/doi/<path:doi>/",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status {response.status_code}")
            else:
                response.success()
