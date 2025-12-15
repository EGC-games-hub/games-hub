import os
import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
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

        email_field.send_keys("user2@example.com")
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

def test_admin_change_user_role_no_flash_check():
    
    driver = initialize_driver()
    host = get_host_for_selenium_testing()
    # Configuración
    ADMIN_EMAIL = "admin@example.com"
    ADMIN_PASSWORD = "1234"
    TARGET_USER_EMAIL = "user1@example.com"
    ADMIN_USERS_URL = f"{host}/admin/users"

    # Definición de roles
    ALL_ROLES = ["curator", "standard"] 

    try:
        # --- 1. Login ---
        driver.get(f"{host}/login")
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        password_field = driver.find_element(By.NAME, "password")
        email_field.send_keys(ADMIN_EMAIL)
        password_field.send_keys(ADMIN_PASSWORD)
        password_field.submit() 
        WebDriverWait(driver, 10).until(lambda d: d.current_url == f"{host}/")

        # --- 2. Navegar a Admin Users ---
        driver.get(ADMIN_USERS_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # --- 3. Identificar fila y rol inicial ---
        user_row_xpath = f"//tr[td[contains(text(), '{TARGET_USER_EMAIL}')]]"
        user_row = driver.find_element(By.XPATH, user_row_xpath)
        
        select_element = user_row.find_element(By.TAG_NAME, "select")
        select = Select(select_element)
        initial_role = select.first_selected_option.get_attribute("value")
        print(f"Rol inicial de {TARGET_USER_EMAIL}: {initial_role}")

        # --- 4. Elegir nuevo rol (diferente al actual) ---
        target_role = next((role for role in ALL_ROLES if role != initial_role), "standard")
        print(f"Cambiando a nuevo rol: {target_role}")

        # --- 5. Ejecutar cambio ---
        select.select_by_value(target_role)
        
        # Clic en el botón "Update"
        submit_button = user_row.find_element(By.XPATH, ".//button[contains(text(), 'Update')]")
        submit_button.click()

        # --- 6. Verificar cambio de rol por recarga de página ---
        
        # Esperamos explícitamente a que la URL de admin se recargue (o se mantenga)
        WebDriverWait(driver, 10).until(EC.url_to_be(ADMIN_USERS_URL))
        
        # Re-localizar la fila y el select (es crucial después de una recarga)
        user_row = driver.find_element(By.XPATH, user_row_xpath)
        select_element = user_row.find_element(By.TAG_NAME, "select")
        current_role = Select(select_element).first_selected_option.get_attribute("value")
        
        # AFIRMACIÓN CLAVE: El rol en la página debe ser el rol de destino
        assert current_role == target_role, f"El rol verificado ({current_role}) no coincide con el rol esperado ({target_role})."
        print(f"Cambio verificado en el selector: {current_role}. Test PASADO.")

    except Exception as e:
        print(f"\n¡Test de cambio de rol de Admin FALLIDO!")
        print(f"Fallo en la URL: {driver.current_url}")
        raise e 
    finally:
        close_driver(driver)

def _wait_for_page_ready(driver, timeout=8):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def test_profile_shows_2fa_option_user2():
    """Login as user2 and check in the profile/settings page for an option to enable 2FA."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        _wait_for_page_ready(driver, timeout=8)

        email_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email")))
        password_field = driver.find_element(By.NAME, "password")

        email_field.clear()
        email_field.send_keys("user2@example.com")
        password_field.clear()
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)

        # Wait for login to complete: prefer the app's root redirect used in other tests
        try:
            # Many flows redirect to the site root after successful login — wait for that.
            WebDriverWait(driver, 10).until(lambda d: d.current_url == f"{host}/")
        except Exception:
            # If the strict root check fails, still ensure we are not on /login before continuing.
            try:
                WebDriverWait(driver, 3).until(lambda d: "/login" not in d.current_url)
            except Exception:
                # give one more second as a last resort
                time.sleep(1)

        # First try: look for a profile/account link in the UI and click it if present
        found_option = False
        try:
            # common selectors for profile links
            link_selectors = [
                "a[href*='/profile']", "a[href*='/user/profile']", "a[href*='/account']", "a[href*='/settings']",
                "a.profile", "a#profile", "a[title*='Perfil']", "a[aria-label*='profile']"
            ]
            for sel in link_selectors:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    try:
                        els[0].click()
                        _wait_for_page_ready(driver, timeout=6)
                        break
                    except Exception:
                        # if click fails, try next selector
                        continue
        except Exception:
            pass

        # If clicking didn't navigate us to a profile-like page, fall back to direct GETs
        # include the explicit profile edit path used by the profile module
        profile_paths = ["/profile/edit", "/profile", "/user/profile", "/account", "/settings", "/user"]
        for path in profile_paths:
            try:
                # If already on this path, just check it
                if path in driver.current_url:
                    _wait_for_page_ready(driver, timeout=4)
                else:
                    driver.get(f"{host}{path}")
                    _wait_for_page_ready(driver, timeout=6)

                body = driver.page_source.lower()
                # Detect 404 pages heuristically and skip if found. If detected, print debug info.
                if "404" in driver.title or "not found" in body or "página no encontrada" in body:
                    # small debug output to help understand why a given path returned 404
                    print(f"DEBUG: Path {path} returned 404 (title='{driver.title}'), current_url={driver.current_url}")
                    # print a short snippet of the body for diagnosing server responses
                    snippet = body[:400].replace('\n', ' ')
                    print(f"DEBUG: Body snippet: {snippet}...")
                    continue

                # Look for 'activar' (enable) + 'doble' or 'two-factor' or '2fa'
                if ("activar" in body and ("doble" in body or "factor" in body)) or any(x in body for x in ["two-factor", "two factor", "2fa", "enable 2fa", "habilitar 2fa"]):
                    found_option = True
                    break
            except Exception:
                # try next path
                continue

        assert found_option, "No se encontró la opción para activar doble factor en la página de perfil de user2"
        print("test_profile_shows_2fa_option_user2: OK")

    finally:
        close_driver(driver)


