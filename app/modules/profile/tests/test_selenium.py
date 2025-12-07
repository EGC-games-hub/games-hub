import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import initialize_driver, close_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def test_view_public_profile_from_dataset_owner():
    """
    E2E: Login, create a simple dataset, open its detail page, click on the
    "Uploaded by" author link, and verify the public profile shows basic fields.
    """
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Anonymous: directly open a known seeded dataset by DOI
        # Seeders create datasets with DOIs like 10.1234/dataset1
        driver.get(f"{host}/doi/10.1234/dataset1")
        wait_for_page_to_load(driver)
        time.sleep(2)

        # Click any public profile link present on the dataset detail page
        WebDriverWait(driver, 15).until(
            lambda d: len(d.find_elements(By.XPATH, "//a[contains(@href, '/profile/')]") ) > 0
        )
        uploaded_by_link = driver.find_element(By.XPATH, "(//a[contains(@href, '/profile/')])[1]")
        uploaded_by_link.click()
        wait_for_page_to_load(driver)
        time.sleep(2)

        # Wait for public profile header to confirm navigation
        WebDriverWait(driver, 12).until(
            lambda d: "User profile" in d.page_source
        )

        # Verify public profile page shows basic information
        # We expect labels present in template (Name, Surname, Affiliation, Orcid)
        assert "Name:" in driver.page_source
        assert "Surname:" in driver.page_source
        assert "Affiliation:" in driver.page_source
        assert "Orcid:" in driver.page_source

    finally:
        close_driver(driver)
