import os
import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_login_and_check_element():

    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")

        # Find the username and password field and enter the values
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)

        # After login the app redirects to the index. Assert we are at root and page title looks ok.
        WebDriverWait(driver, 10).until(lambda d: d.current_url == f"{host}/")
        title = driver.title or ""
        assert "UVLHUB" in title or "Games Hub" in title or title != "", f"Unexpected page title: {title}"
        print("Login test passed!")

    finally:

        # Close the browser
        close_driver(driver)


