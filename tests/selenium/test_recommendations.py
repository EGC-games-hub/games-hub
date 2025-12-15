import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
DOI_PATH = os.getenv("TEST_DOI_PATH", "10.1234/dataset4")

@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_dataset_page_shows_recommendations(driver):
    
    driver.get(f"{BASE_URL}/doi/{DOI_PATH}/")

    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    
    h1s = driver.find_elements(By.TAG_NAME, "h1")
    if h1s and h1s[0].text.strip() in {"404", "400"}:
        driver.save_screenshot("selenium_fail.png")
        raise AssertionError(f"Página de error. URL={driver.current_url}")

   
    elems = driver.find_elements(
        By.XPATH,
        "//*[contains(translate(., 'RECOMMEND', 'recommend'), 'recommend') "
        "or contains(translate(., 'RECOMEND', 'recomend'), 'recomend')]"
    )

    if not elems:
        driver.save_screenshot("selenium_fail.png")
        with open("selenium_fail.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    assert elems, "No se encontró bloque de recomendaciones. Mira selenium_fail.html"
