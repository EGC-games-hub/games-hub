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


<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> f286711 (fix: Arreglo para el flujo)
def initialize_driver():
    """
    Initialize the WebDriver depending on the environment.
    - Local: uses webdriver-manager
    - CI or Docker: headless mode (CI detection)
    """
<<<<<<< HEAD
    working_dir = os.environ.get("WORKING_DIR", "")
    selenium_hub_url = "http://selenium-hub:4444/wd/hub"
    driver_name = get_service_driver()  # tu función existente

    # Detect CI environment
    is_ci = os.environ.get("CI") == "true"

=======
ddef initialize_driver():
=======
>>>>>>> f286711 (fix: Arreglo para el flujo)
    working_dir = os.environ.get("WORKING_DIR", "")
    selenium_hub_url = "http://selenium-hub:4444/wd/hub"
    driver_name = get_service_driver()  # tu función existente

    # Detect CI environment
    is_ci = os.environ.get("CI") == "true"

>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
=======
ddef initialize_driver():
    working_dir = os.environ.get("WORKING_DIR", "")
    driver_name = get_service_driver()

>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
    # Firefox Snap TMPDIR fix
    if driver_name == "firefox":
        snap_tmp = os.path.expanduser("~/snap/firefox/common/tmp")
        os.makedirs(snap_tmp, exist_ok=True)
        os.environ["TMPDIR"] = snap_tmp

    # Remote mode (Selenium Grid)
    if working_dir == "/app/":
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
        options = None
=======
        selenium_hub_url = "http://selenium-hub:4444/wd/hub"
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
=======
        options = None
>>>>>>> f286711 (fix: Arreglo para el flujo)
=======
        selenium_hub_url = "http://selenium-hub:4444/wd/hub"
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
        if driver_name == "chrome":
            options = webdriver.ChromeOptions()
        elif driver_name == "firefox":
            options = webdriver.FirefoxOptions()
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
            options.add_argument("--headless")  # <--- headless
            driver = webdriver.Remote(command_executor=selenium_hub_url, options=options)
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
        else:
            raise Exception(f"Driver '{driver_name}' not supported.")
=======
        else:
            raise Exception(f"Driver '{driver_name}' not supported.")

<<<<<<< HEAD
        if is_ci:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        return webdriver.Remote(command_executor=selenium_hub_url, options=options)

>>>>>>> f286711 (fix: Arreglo para el flujo)

<<<<<<< HEAD
        if is_ci:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        return webdriver.Remote(command_executor=selenium_hub_url, options=options)


    # Local mode
    if driver_name == "chrome":
        options = webdriver.ChromeOptions()
        if is_ci:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
=======
    # Local mode
    if driver_name == "chrome":
        options = webdriver.ChromeOptions()
<<<<<<< HEAD
        if os.environ.get("CI"):
            options.add_argument("--headless")  # headless en CI
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
=======
        if is_ci:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
>>>>>>> f286711 (fix: Arreglo para el flujo)
=======
    # Local mode
    if driver_name == "chrome":
        options = webdriver.ChromeOptions()
        if os.environ.get("CI"):
            options.add_argument("--headless")  # headless en CI
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

    elif driver_name == "firefox":
        options = webdriver.FirefoxOptions()
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
        if is_ci:
            options.add_argument("--headless")
=======
        if os.environ.get("CI"):
            options.add_argument("--headless")  # headless en CI
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
=======
        if is_ci:
            options.add_argument("--headless")
>>>>>>> f286711 (fix: Arreglo para el flujo)
=======
        if os.environ.get("CI"):
            options.add_argument("--headless")  # headless en CI
>>>>>>> 4c99a6b (fix: Arreglar driver para que funcionen los test)
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)

    else:
        raise Exception(f"Driver '{driver_name}' not supported.")

    return driver


def close_driver(driver):
    """Safely quit the browser."""
    if driver:
        driver.quit()
