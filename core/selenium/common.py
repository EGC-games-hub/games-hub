import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


def get_service_driver():
    """Return the configured browser driver (chrome or firefox)."""
    return os.environ.get("SERVICE_DRIVER", "firefox").lower()


def set_service_driver(driver="firefox"):
    """Set the browser driver dynamically."""
    os.environ["SERVICE_DRIVER"] = driver.lower()


ddef initialize_driver():
    working_dir = os.environ.get("WORKING_DIR", "")
    driver_name = get_service_driver()

    # Firefox Snap TMPDIR fix
    if driver_name == "firefox":
        snap_tmp = os.path.expanduser("~/snap/firefox/common/tmp")
        os.makedirs(snap_tmp, exist_ok=True)
        os.environ["TMPDIR"] = snap_tmp

    # Remote mode (Selenium Grid)
    if working_dir == "/app/":
        selenium_hub_url = "http://selenium-hub:4444/wd/hub"
        if driver_name == "chrome":
            options = webdriver.ChromeOptions()
            driver = webdriver.Remote(command_executor=selenium_hub_url, options=options)
        elif driver_name == "firefox":
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")  # <--- headless
            driver = webdriver.Remote(command_executor=selenium_hub_url, options=options)
        else:
            raise Exception(f"Driver '{driver_name}' not supported.")
        return driver

    # Local mode
    if driver_name == "chrome":
        options = webdriver.ChromeOptions()
        if os.environ.get("CI"):
            options.add_argument("--headless")  # headless en CI
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

    elif driver_name == "firefox":
        options = webdriver.FirefoxOptions()
        if os.environ.get("CI"):
            options.add_argument("--headless")  # headless en CI
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)

    else:
        raise Exception(f"Driver '{driver_name}' not supported.")

    return driver


def close_driver(driver):
    """Safely quit the browser."""
    if driver:
        driver.quit()
