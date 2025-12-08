import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_login_and_check_element():

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)

        # Wait a little while to ensure that the action has been completed
        time.sleep(4)

        try:

            driver.find_element(By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]")
            print("Test passed!")

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:

        # Close the browser
        close_driver(driver)


# Note: Do not call test functions at import time. pytest will collect and run them.


def test_admin_change_user_role_ui():
    """UI test: as an admin, change a user's role via the admin users page.

    This test requires environment variables ADMIN_EMAIL and ADMIN_PASSWORD to point
    to a valid admin user on the running test server. If not set, the test is skipped.
    """
    import os
    from selenium.webdriver.support.ui import Select
    import pytest

    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        pytest.skip("ADMIN_EMAIL and ADMIN_PASSWORD not set; skipping admin role UI test")

    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Login page
        driver.get(f"{host}/login")
        time.sleep(2)
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")
        email_field.clear()
        password_field.clear()
        email_field.send_keys(admin_email)
        password_field.send_keys(admin_password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(2)

        # Navigate to admin users
        driver.get(f"{host}/admin/users")
        time.sleep(2)

        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
        target_row = None
        target_email = None
        for row in rows:
            email_text = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
            role_text = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
            if email_text != admin_email:
                target_row = row
                target_email = email_text
                break

        assert target_row is not None, "No non-admin user found to change role"

        current_role = target_row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
        select_el = target_row.find_element(By.TAG_NAME, "select")
        select = Select(select_el)
        new_role = "curator" if current_role != "curator" else "standard"
        select.select_by_value(new_role)

        # Submit
        btn = target_row.find_element(By.CSS_SELECTOR, "button[type='submit']")
        btn.click()
        time.sleep(2)

        # Reload and verify
        driver.get(f"{host}/admin/users")
        time.sleep(2)
        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
        found = False
        for row in rows:
            email_text = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
            if email_text == target_email:
                role_text = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
                assert role_text == new_role, f"Expected role {new_role}, got {role_text}"
                found = True
                break

        assert found, "Updated user row not found after role change"

    finally:
        close_driver(driver)

# Note: Do not call test functions at import time. pytest will collect and run them.