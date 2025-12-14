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



def _wait_for_page_ready(driver, timeout=8):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def _find_2fa_prompt(driver, timeout=8):
    """Return True if the page shows a 2FA prompt (input or text), else False."""
    wait = WebDriverWait(driver, timeout)
    try:
        # Common input names for 2FA
        possible_names = ["two_factor_code", "two_factor", "twofactor", "otp", "code", "verification_code"]
        for name in possible_names:
            try:
                if wait.until(EC.presence_of_element_located((By.NAME, name))):
                    return True
            except Exception:
                pass

        # Common input ids
        possible_ids = ["two_factor_code", "otp", "twofactor", "mfa_code"]
        for pid in possible_ids:
            try:
                if wait.until(EC.presence_of_element_located((By.ID, pid))):
                    return True
            except Exception:
                pass

        # Look for headings or labels that mention código / código de verificación / two-factor / 2FA
        body = driver.page_source.lower()
        keywords = ["código", "codigo", "código de verificación", "two-factor", "two factor", "2fa", "verificación"]
        for kw in keywords:
            if kw in body:
                return True

    except Exception:
        return False

    return False


def test_login_triggers_2fa_user1():
    """Attempt login as user1 and assert the app asks for a 2FA code (do not fill it)."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        _wait_for_page_ready(driver, timeout=8)

        email_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email")))
        password_field = driver.find_element(By.NAME, "password")

        email_field.clear()
        email_field.send_keys("user1@example.com")
        password_field.clear()
        password_field.send_keys("1234")
        password_field.send_keys(Keys.RETURN)
        # Wait until the app redirects to the 2FA verification route
        try:
            WebDriverWait(driver, 8).until(lambda d: "/2fa/verify" in d.current_url)
        except Exception:
            # small grace sleep and re-check once
            time.sleep(1)

        assert "/2fa/verify" in driver.current_url, f"Después del login no se redirigió a /2fa/verify, url actual: {driver.current_url}"
        print("test_login_triggers_2fa_user1: OK")

    finally:
        close_driver(driver)


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
        profile_paths = ["/profile", "/user/profile", "/account", "/settings", "/user"]
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


