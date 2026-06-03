"""
Selenium Execution Engine
-------------------------
conftest.py-compatible fixtures and a base PageObject class.
Generated test scripts import from here.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from dotenv import load_dotenv

load_dotenv()

BROWSER       = os.getenv("SELENIUM_BROWSER", "chrome").lower()
HEADLESS      = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"
BASE_URL      = os.getenv("SELENIUM_BASE_URL", "http://localhost:3000")
IMPLICIT_WAIT = int(os.getenv("SELENIUM_IMPLICIT_WAIT", "10"))
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./reports/screenshots")


# ── Pytest fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def driver():
    """Session-scoped WebDriver. Quits after all tests in the session."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    _driver = _build_driver()
    _driver.implicitly_wait(IMPLICIT_WAIT)
    _driver.maximize_window()
    yield _driver
    _driver.quit()


@pytest.fixture(autouse=True)
def screenshot_on_failure(request, driver):
    """Auto-capture screenshot on test failure."""
    yield
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        name = request.node.name.replace("/", "_")
        path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
        driver.save_screenshot(path)
        print(f"\nScreenshot saved: {path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


# ── Driver factory ─────────────────────────────────────────────────────────────

def _build_driver():
    if BROWSER == "firefox":
        opts = FirefoxOptions()
        if HEADLESS:
            opts.add_argument("--headless")
        return webdriver.Firefox(
            service=FirefoxService(GeckoDriverManager().install()),
            options=opts,
        )
    else:  # default: chrome
        opts = ChromeOptions()
        if HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        return webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=opts,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Base Page Object
# ══════════════════════════════════════════════════════════════════════════════

class BasePage:
    """
    All Page Object classes inherit from this.
    Provides safe wrappers around common Selenium interactions.
    """

    DEFAULT_TIMEOUT = IMPLICIT_WAIT

    def __init__(self, driver: webdriver.Remote):
        self.driver = driver
        self.wait   = WebDriverWait(driver, self.DEFAULT_TIMEOUT)
        self.base_url = BASE_URL

    def navigate(self, path: str = ""):
        self.driver.get(f"{self.base_url}{path}")

    def find(self, by: str, value: str):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def click(self, by: str, value: str):
        el = self.wait.until(EC.element_to_be_clickable((by, value)))
        el.click()
        return el

    def type_text(self, by: str, value: str, text: str):
        el = self.find(by, value)
        el.clear()
        el.send_keys(text)
        return el

    def get_text(self, by: str, value: str) -> str:
        return self.find(by, value).text

    def is_visible(self, by: str, value: str, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except Exception:
            return False

    def wait_for_url(self, partial_url: str, timeout: int = 10):
        WebDriverWait(self.driver, timeout).until(
            EC.url_contains(partial_url)
        )

    def get_title(self) -> str:
        return self.driver.title

    def take_screenshot(self, name: str):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
        self.driver.save_screenshot(path)
        return path
