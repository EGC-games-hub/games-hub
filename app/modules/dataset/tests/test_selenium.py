import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

        # Obtain the absolute paths of the files
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


# Do not call tests at import time. pytest will discover and run them.


def test_post_comment():
    """Selenium test that posts a comment on the first dataset visible to the user.

    Flow:
    - Login as user2@example.com
    - If no datasets exist, perform a minimal upload to create one
    - Open the first dataset's view page
    - Post a unique comment and assert it appears on the page
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user2@example.com")
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Ensure at least one dataset exists; if not, upload a minimal one
        if count_datasets(driver, host) == 0:
            driver.get(f"{host}/dataset/upload")
            wait_for_page_to_load(driver)

            title_field = driver.find_element(By.NAME, "title")
            title_field.send_keys("Comment test dataset")
            desc_field = driver.find_element(By.NAME, "desc")
            desc_field.send_keys("Description")
            tags_field = driver.find_element(By.NAME, "tags")
            tags_field.send_keys("tag1")

            # Add one author
            add_author_button = driver.find_element(By.ID, "add_author")
            add_author_button.send_keys(Keys.RETURN)
            wait_for_page_to_load(driver)

            name_field0 = driver.find_element(By.NAME, "authors-0-name")
            name_field0.send_keys("Author0")
            affiliation_field0 = driver.find_element(By.NAME, "authors-0-affiliation")
            affiliation_field0.send_keys("Club0")
            orcid_field0 = driver.find_element(By.NAME, "authors-0-orcid")
            orcid_field0.send_keys("0000-0000-0000-0000")

            # Upload a small example UVL file
            file1_path = os.path.abspath("app/modules/dataset_csv/csv_example/valid.csv")
            dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
            dropzone.send_keys(file1_path)
            wait_for_page_to_load(driver)

            # Agree and submit
            check = driver.find_element(By.ID, "agreeCheckbox")
            check.send_keys(Keys.SPACE)
            wait_for_page_to_load(driver)
            upload_btn = driver.find_element(By.ID, "upload_button")
            upload_btn.send_keys(Keys.RETURN)
            wait_for_page_to_load(driver)
            time.sleep(2)

        # Open the dataset list and click the first dataset link
        driver.get(f"{host}/dataset/list")
        wait_for_page_to_load(driver)

        # First dataset anchor is in the first table row first cell
        first_link = driver.find_element(By.XPATH, "//table//tbody//tr[1]//td[1]//a")
        first_link.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        # Post a comment
        comment_text = f"Selenium comment {int(time.time())}"

        # Wait for the comment textarea to be present and visible. If the
        # element is inside an iframe this will fail and we will capture
        # debugging artifacts (screenshot and page HTML) to help diagnosis.
        try:
            textarea = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.NAME, "content"))
            )
        except Exception:
            # Capture debug info to workspace for investigation
            try:
                driver.save_screenshot("selenium_post_comment_error.png")
            except Exception:
                pass
            try:
                with open("selenium_post_comment_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except Exception:
                pass
            raise

        textarea.send_keys(comment_text)

        post_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post comment')]") )
        )
        post_btn.send_keys(Keys.RETURN)

        # Wait for redirect and rendering
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Verify the comment is present in the page
        comments = driver.find_elements(By.XPATH, f"//p[contains(text(), '{comment_text}')]")
        assert len(comments) >= 1, "Posted comment not found on the dataset page"

        print("Comment test passed!")

    finally:
        close_driver(driver)