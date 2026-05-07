"""
keep_alive.py — LexiAssist Streamlit Keep-Alive Script
Uses Selenium with headless Chrome to establish a real browser/WebSocket
connection to the app, which is the only request type Streamlit counts
as genuine traffic.

Run via GitHub Actions every 6 hours (see .github/workflows/keep_alive.yml).
"""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "").strip()

if not STREAMLIT_URL:
    print("❌  STREAMLIT_URL environment variable is not set.")
    print("    Add it as a GitHub Actions secret named STREAMLIT_URL.")
    sys.exit(1)


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")          # headless Chrome (new mode)
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def ping_app(driver: webdriver.Chrome) -> bool:
    print(f"🌐  Opening: {STREAMLIT_URL}")
    driver.get(STREAMLIT_URL)

    # ── Case 1: App is sleeping — click the wake button if present ──────
    try:
        wake_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), 'get this app back up')]")
            )
        )
        print("💤  App was sleeping — clicking wake button...")
        wake_btn.click()
        # Wait for the app to fully boot (can take 30–60 s on cold start)
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        print("✅  App woken successfully.")
    except Exception:
        pass  # App was already awake — no wake button found

    # ── Case 2: App is running — wait for Streamlit iframe / main content ─
    try:
        WebDriverWait(driver, 60).until(
            lambda d: (
                d.execute_script("return document.readyState") == "complete"
                and len(d.find_elements(By.TAG_NAME, "iframe")) > 0
            )
        )
        print("✅  App is alive and fully loaded.")
        return True
    except Exception:
        # Fallback: at minimum the page loaded (app may have crashed / errored)
        page_title = driver.title
        print(f"⚠️   App page loaded but iframe not found. Title: '{page_title}'")
        print("    App may be erroring — check your Streamlit Cloud logs.")
        return False


def main():
    driver = build_driver()
    try:
        success = ping_app(driver)
        # Keep WebSocket alive for 30 s — Streamlit counts sustained connections
        if success:
            print("⏳  Holding connection for 30 s to register as real traffic...")
            time.sleep(30)
            print("✅  Done. App will remain awake for the next 12 h.")
        else:
            sys.exit(1)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
