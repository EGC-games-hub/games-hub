import logging
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from flask import Response, jsonify
from flask_login import current_user

from app.modules.dataset.models import DataSet
from app.modules.featuremodel.models import FeatureModel
from app.modules.zenodo.repositories import ZenodoRepository
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)

load_dotenv()


class ZenodoService(BaseService):

    def _build_session(self) -> requests.Session:
        """Create a requests session with retry/backoff for rate limits and transient errors."""
        session = requests.Session()
        retry = Retry(
            total=int(os.getenv("ZENODO_RETRY_TOTAL", "5")),
            connect=int(os.getenv("ZENODO_RETRY_CONNECT", "3")),
            read=int(os.getenv("ZENODO_RETRY_READ", "3")),
            status=int(os.getenv("ZENODO_RETRY_STATUS", "5")),
            backoff_factor=float(os.getenv("ZENODO_BACKOFF", "1.5")),
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST", "DELETE", "PUT"),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Wrapper around session.request that adds explicit 429 handling (Retry-After)."""
        resp = self.session.request(method=method, url=url, **kwargs)
        if resp.status_code == 429:
            # Honor Retry-After if provided
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    sleep_s = int(retry_after)
                except ValueError:
                    sleep_s = 5
            else:
                sleep_s = int(os.getenv("ZENODO_RATEWAIT", "5"))
            logger.warning(f"Rate limited (429). Sleeping {sleep_s}s then retrying {method} {url}")
            time.sleep(sleep_s)
            resp = self.session.request(method=method, url=url, **kwargs)
        return resp

    def _resolve_base_url(self) -> str:
        """Return base API URL (forced to fakenodo to avoid calling real Zenodo)."""
        mode = "fake"
        if mode == "fake":
            # Priority: FAKENODO_URL (supports lowercase alias), gateway detection, localhost
            fakenodo_url = (
                os.getenv("FAKENODO_URL")
                or os.getenv("fakenodo_url")
                or os.getenv("FAKENODO_BASE_URL")
                or os.getenv("fakenodo_base_url")
            )
            if fakenodo_url:
                url = fakenodo_url.rstrip("/")
                # Accept base service URL and append deposit path if missing
                if "deposit/depositions" not in url:
                    url = f"{url}/deposit/depositions"
                return url
            try:
                if os.path.exists("/proc/net/route"):
                    with open("/proc/net/route") as f:
                        for line in f.readlines()[1:]:
                            parts = line.strip().split()
                            if len(parts) >= 3 and parts[1] == "00000000":
                                gw_hex = parts[2]
                                gw = ".".join(str(int(gw_hex[i : i + 2], 16)) for i in range(6, -1, -2))
                                candidate = f"http://{gw}:5001/deposit/depositions"
                                return candidate.rstrip("/")
            except Exception:
                pass
            return "http://localhost:5001/deposit/depositions"
        # Sandbox/prod intentionally disabled
        # If needed in the future, re-enable with explicit opt-in and throttling.
        # For now we always use fakenodo.
        


    def get_zenodo_access_token(self):
        return os.getenv("ZENODO_ACCESS_TOKEN")

    def __init__(self):
        super().__init__(ZenodoRepository())
        # Force fake mode to avoid calling real Zenodo
        self.mode = "fake"
        self.ZENODO_API_URL = self._resolve_base_url()
        self.ZENODO_ACCESS_TOKEN = None
        # Build headers
        self.headers = {"Content-Type": "application/json"}
        # Query params (none by default)
        self.params = {}
        # Session with retries
        self.session = self._build_session()

    def test_connection(self) -> bool:
        """
        Test the connection with Fakenodo.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        response = self._request("GET", self.ZENODO_API_URL, params=self.params, headers=self.headers)
        return response.status_code == 200

    def test_full_connection(self) -> Response:
        """
        Test the connection with Fakenodo by creating a deposition, uploading an empty test file, and deleting the
        deposition.

        Returns:
            bool: True if the connection, upload, and deletion are successful, False otherwise.
        """
        success = True

        # Create a test file
        working_dir = os.getenv("WORKING_DIR", "")
        file_path = os.path.join(working_dir, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("This is a test file with some content.")

        messages = []  # List to store messages

    # Step 1: Create a deposition on Fakenodo
        data = {
            "metadata": {
                "title": "Test Deposition",
                "upload_type": "dataset",
                "description": "This is a test deposition created via Zenodo API",
                "creators": [{"name": "John Doe"}],
            }
        }

        response = self._request("POST", self.ZENODO_API_URL, json=data, params=self.params, headers=self.headers)

        if response.status_code != 201:
            return jsonify(
                {
                    "success": False,
                    "messages": f"Failed to create test deposition on Zenodo. Response code: {response.status_code}",
                }
            )

        deposition_id = response.json()["id"]

        # Step 2: Upload an empty file to the deposition
        data = {"name": "test_file.txt"}
        files = {"file": open(file_path, "rb")}
        publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/files"
        response = self._request("POST", publish_url, params=self.params, data=data, files=files)
        files["file"].close()  # Close the file after uploading

        logger.info(f"Publish URL: {publish_url}")
        logger.info(f"Params: {self.params}")
        logger.info(f"Data: {data}")
        logger.info(f"Files: {files}")
        logger.info(f"Response Status Code: {response.status_code}")
        logger.info(f"Response Content: {response.content}")

        if response.status_code != 201:
            messages.append(f"Failed to upload test file to Fakenodo. Response code: {response.status_code}")
            success = False

        # Step 3: Delete the deposition
        response = self._request("DELETE", f"{self.ZENODO_API_URL}/{deposition_id}", params=self.params)

        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({"success": success, "messages": messages})

    def get_all_depositions(self) -> dict:
        """
        Get all depositions from Zenodo.

        Returns:
            dict: The response in JSON format with the depositions.
        """
        response = self._request("GET", self.ZENODO_API_URL, params=self.params, headers=self.headers)
        if response.status_code != 200:
            raise Exception("Failed to get depositions")
        return response.json()

    def create_new_deposition(self, dataset: DataSet) -> dict:
        """
        Create a new deposition in Zenodo.

        Args:
            dataset (DataSet): The DataSet object containing the metadata of the deposition.

        Returns:
            dict: The response in JSON format with the details of the created deposition.
        """

        logger.info("Dataset sending to Zenodo...")
        logger.info(f"Publication type...{dataset.ds_meta_data.publication_type.value}")

        metadata = {
            "title": dataset.ds_meta_data.title,
            "upload_type": "dataset" if dataset.ds_meta_data.publication_type.value == "none" else "publication",
            "publication_type": (
                dataset.ds_meta_data.publication_type.value
                if dataset.ds_meta_data.publication_type.value != "none"
                else None
            ),
            "description": dataset.ds_meta_data.description,
            "creators": [
                {
                    "name": author.name,
                    **({"affiliation": author.affiliation} if author.affiliation else {}),
                    **({"orcid": author.orcid} if author.orcid else {}),
                }
                for author in dataset.ds_meta_data.authors
            ],
            "keywords": (
                ["uvlhub"] if not dataset.ds_meta_data.tags else dataset.ds_meta_data.tags.split(", ") + ["uvlhub"]
            ),
            "access_right": "open",
            "license": "CC-BY-4.0",
        }

        data = {"metadata": metadata}

        response = self._request("POST", self.ZENODO_API_URL, params=self.params, json=data, headers=self.headers)
        if response.status_code != 201:
            # Try to extract JSON error if possible, otherwise include raw text
            try:
                details = response.json()
            except Exception:
                details = response.text
            error_message = f"Failed to create deposition. Status: {response.status_code}. Details: {details}"
            raise Exception(error_message)
        try:
            return response.json()
        except Exception:
            # If response is not JSON (unexpected), return raw text in a dict
            return {"raw_response": response.text}

    def upload_file(self, dataset: DataSet, deposition_id: int, feature_model: FeatureModel, user=None) -> dict:
        """
        Upload a file to a deposition in Zenodo.

        Args:
            deposition_id (int): The ID of the deposition in Zenodo.
            feature_model (FeatureModel): The FeatureModel object representing the feature model.
            user (FeatureModel): The User object representing the file owner.

        Returns:
            dict: The response in JSON format with the details of the uploaded file.
        """
        uvl_filename = feature_model.fm_meta_data.uvl_filename
        data = {"name": uvl_filename}
        user_id = current_user.id if user is None else user.id
        file_path = os.path.join(uploads_folder_name(), f"user_{str(user_id)}", f"dataset_{dataset.id}/", uvl_filename)
        files = {"file": open(file_path, "rb")}

        publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/files"
        response = self._request("POST", publish_url, params=self.params, data=data, files=files)
        files["file"].close()
        if response.status_code != 201:
            error_message = f"Failed to upload files. Error details: {response.json()}"
            raise Exception(error_message)
        return response.json()

    def publish_deposition(self, deposition_id: int) -> dict:
        """
        Publish a deposition in Zenodo.

        Args:
            deposition_id (int): The ID of the deposition in Zenodo.

        Returns:
            dict: The response in JSON format with the details of the published deposition.
        """
        publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/actions/publish"
        response = self._request("POST", publish_url, params=self.params, headers=self.headers)
        if response.status_code != 202:
            raise Exception("Failed to publish deposition")
        return response.json()

    def get_deposition(self, deposition_id: int) -> dict:
        """
        Get a deposition from Zenodo.

        Args:
            deposition_id (int): The ID of the deposition in Zenodo.

        Returns:
            dict: The response in JSON format with the details of the deposition.
        """
        deposition_url = f"{self.ZENODO_API_URL}/{deposition_id}"
        response = self._request("GET", deposition_url, params=self.params, headers=self.headers)
        if response.status_code != 200:
            raise Exception("Failed to get deposition")
        return response.json()

    def get_doi(self, deposition_id: int) -> str:
        """
        Get the DOI of a deposition from Zenodo.

        Args:
            deposition_id (int): The ID of the deposition in Zenodo.

        Returns:
            str: The DOI of the deposition.
        """
        return self.get_deposition(deposition_id).get("doi")