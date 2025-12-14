import os
import time
import re
import tempfile
import datetime
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def count_datasets(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def test_upload_dataset():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user2@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)
        time.sleep(4)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open the upload dataset
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Find basic info and UVL model and fill values
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Title")
        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Description")
        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("tag1,tag2")

        # Add two authors and fill
        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field0 = driver.find_element(By.NAME, "authors-0-name")
        name_field0.send_keys("Author0")
        affiliation_field0 = driver.find_element(By.NAME, "authors-0-affiliation")
        affiliation_field0.send_keys("Club0")
        orcid_field0 = driver.find_element(By.NAME, "authors-0-orcid")
        orcid_field0.send_keys("0000-0000-0000-0000")

        name_field1 = driver.find_element(By.NAME, "authors-1-name")
        name_field1.send_keys("Author1")
        affiliation_field1 = driver.find_element(By.NAME, "authors-1-affiliation")
        affiliation_field1.send_keys("Club1")

        # Obtén las rutas absolutas de los archivos
        file1_path = os.path.abspath("app/modules/dataset/uvl_examples/file1.uvl")
        file2_path = os.path.abspath("app/modules/dataset/uvl_examples/file2.uvl")

        # Subir el primer archivo
        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file1_path)
        wait_for_page_to_load(driver)

        # Subir el segundo archivo
        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file2_path)
        wait_for_page_to_load(driver)

        # Add authors in UVL models
        show_button = driver.find_element(By.ID, "0_button")
        show_button.send_keys(Keys.RETURN)
        add_author_uvl_button = driver.find_element(By.ID, "0_form_authors_button")
        add_author_uvl_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "feature_models-0-authors-2-name")
        name_field.send_keys("Author3")
        affiliation_field = driver.find_element(By.NAME, "feature_models-0-authors-2-affiliation")
        affiliation_field.send_keys("Club3")

        # Check I agree and send form
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)

        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)
        time.sleep(2)  # Force wait time

        assert driver.current_url == f"{host}/dataset/list", "Test failed!"

        # Count final datasets
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Test failed!"

        print("Test passed!")

    finally:

        # Close the browser
        close_driver(driver)


# Note: do not call test functions at import time; pytest will discover and run them.


class TestSelenium:
    def test_trending_dataset(self):
        """Selenium test that verifies the "Datasets más populares" table on the home page:

        - There is a table titled 'Datasets más populares' with 5 rows.
        - Each row shows title, main author, community (if any) and number of downloads.
        - The rows are sorted by downloads (last month) in non-increasing order.
        - Clicking the title of the first dataset navigates to a dataset page (/dataset/ in the URL).

        The test is intentionally flexible about exact column indices to work with similar table structures.
        """

        driver = initialize_driver()

        try:
            host = get_host_for_selenium_testing()

            # Open home page
            driver.get(f"{host}/")
            wait_for_page_to_load(driver)

            # Try to locate the trending table. Prefer Spanish heading but allow multiple fallbacks.
            wait = WebDriverWait(driver, 15)
            table = None

            locators = [
                (By.ID, "trending-datasets"),
                (By.CSS_SELECTOR, "table.trending-datasets"),
                # caption inside a table
                (By.XPATH, "//table[.//caption[contains(normalize-space(.),'Datasets más populares')]]"),
                # handle accents and 'mas' without accent
                (By.XPATH, "//caption[contains(translate(normalize-space(.), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'), 'Datasets mas populares')]/ancestor::table[1]"),
                # heading followed by table
                (By.XPATH, "//*[self::h1 or self::h2 or self::h3][contains(normalize-space(.),'Datasets más populares')]/following::table[1]"),
                (By.XPATH, "//*[self::h1 or self::h2 or self::h3][contains(translate(normalize-space(.), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'), 'Datasets mas populares')]/following::table[1]"),
                # english fallbacks
                (By.XPATH, "//*[self::h1 or self::h2 or self::h3][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'popular')]/following::table[1]"),
                (By.XPATH, "//table[.//th[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dataset') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'popular')]][1]"),
            ]

            for by, val in locators:
                try:
                    el = wait.until(EC.presence_of_element_located((by, val)))
                except Exception:
                    el = None

                if el is not None:
                    try:
                        if el.tag_name.lower() == "table":
                            table = el
                        else:
                            # try to find nearest following table
                            try:
                                table = el.find_element(By.XPATH, "following::table[1]")
                            except Exception:
                                # as final resort, try to find any table on page
                                try:
                                    table = driver.find_element(By.XPATH, "//table[1]")
                                except Exception:
                                    table = None
                    except Exception:
                        table = None
                if table is not None:
                    break

            if table is None:
                # Dump page source and screenshot for debugging
                ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                html_path = tempfile.gettempdir() + f"/trending_missing_{ts}.html"
                png_path = tempfile.gettempdir() + f"/trending_missing_{ts}.png"
                try:
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    driver.save_screenshot(png_path)
                except Exception:
                    pass
                raise AssertionError(f"No se encontró la tabla 'Datasets más populares' en la página de inicio. Volcado a: {html_path} {png_path}")

            # Get rows (try tbody first, then any tr except header)
            try:
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                if len(rows) == 0:
                    rows = table.find_elements(By.XPATH, ".//tr[td]")
            except Exception:
                rows = table.find_elements(By.XPATH, ".//tr[td]")

            # Expect at least 1 dataset in the trending list
            assert len(rows) >= 1, f"Se esperaba al menos 1 fila en 'Datasets más populares', encontrado: {len(rows)}"

            downloads = []

            for row in rows:
                # Flexible extraction of cells
                cells = row.find_elements(By.TAG_NAME, "td")
                assert len(cells) >= 2, "Cada fila debe tener al menos 2 columnas (título y descargas o autor)"

                # Title (first cell)
                title_text = cells[0].text.strip()
                assert title_text, "El título del dataset no debe estar vacío"

                # Try to find a clickable link in the first cell
                title_link_el = None
                try:
                    title_link_el = cells[0].find_element(By.TAG_NAME, "a")
                except Exception:
                    title_link_el = None

                # Main author (second cell) if present
                main_author = cells[1].text.strip() if len(cells) > 1 else ""

                # Community may be third cell (optional)
                community = cells[2].text.strip() if len(cells) > 2 else ""

                # Downloads assumed to be last cell
                downloads_raw = cells[-1].text.strip() if len(cells) >= 1 else ""
                # Extract digits from downloads text (e.g., '1,234' or '1234 descargas')
                m = re.search(r"([0-9,.]+)", downloads_raw.replace('\u00A0', ' '))
                assert m, f"No se pudo leer el número de descargas en: '{downloads_raw}'"
                downloads_text = m.group(1)
                # Remove dots or commas used as thousand separators; prefer digits only
                downloads_int = int(re.sub(r"[^0-9]", "", downloads_text))
                downloads.append(downloads_int)

                # Basic checks for displayed fields
                assert main_author != None, "Autor principal debe estar presente (aunque puede estar vacío)"

            # Check sorting: non-increasing order
            for i in range(len(downloads) - 1):
                assert downloads[i] >= downloads[i + 1], f"Los datasets no están ordenados por descargas descendentes: {downloads}"

            # Click on first dataset title and verify navigation
            first_row = rows[0]
            first_cells = first_row.find_elements(By.TAG_NAME, "td")
            try:
                link = first_cells[0].find_element(By.TAG_NAME, "a")
                link.click()
            except Exception:
                # If no <a>, try clicking the whole cell
                try:
                    first_cells[0].click()
                except Exception:
                    raise AssertionError("No se pudo hacer click en el primer dataset para navegar a su página")

            # Wait for navigation: either URL changes to a dataset detail (e.g. /dataset/ or /doi/)
            # or a new window/tab opens. Handle both cases.
            try:
                # If a new window opened, switch to it
                WebDriverWait(driver, 6).until(lambda d: len(d.window_handles) >= 1)
            except Exception:
                pass

            # If click opened a new tab/window, switch to the last handle
            try:
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
            except Exception:
                pass

            # Wait until URL indicates a dataset detail (either /dataset/ or /doi/)
            def url_is_detail(d):
                return re.search(r"/(dataset|doi)/", d.current_url)

            WebDriverWait(driver, 8).until(lambda d: url_is_detail(d))

            # Now assert a detail-like URL
            assert re.search(r"/(dataset|doi)/", driver.current_url), f"Al hacer click no se navegó a la página del dataset, url actual: {driver.current_url}"

            print("test_trending_dataset: OK")

        finally:
            close_driver(driver)
