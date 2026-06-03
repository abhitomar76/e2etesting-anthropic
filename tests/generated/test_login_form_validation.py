import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# ---------------------------------------------------------------------------
# Configuration constants (would normally live in conftest.py / config.py)
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
DEFAULT_TIMEOUT = 10
LOGIN_PATH = "/login"
DASHBOARD_PATH = "/dashboard"


# ---------------------------------------------------------------------------
# BasePage
# ---------------------------------------------------------------------------
class BasePage:
    """Thin wrapper around WebDriver exposing DRY helper methods."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def navigate(self, path: str = "") -> None:
        """Navigate to BASE_URL + path."""
        try:
            self.driver.get(f"{BASE_URL}{path}")
        except WebDriverException as exc:
            raise RuntimeError(f"Failed to navigate to '{BASE_URL}{path}': {exc}") from exc

    def find(self, by: str, value: str):
        """Return a visible element, waiting up to DEFAULT_TIMEOUT seconds."""
        try:
            return self.wait.until(
                EC.visibility_of_element_located((by, value)),
                message=f"Element not visible: ({by}, '{value}')",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for element ({by}, '{value}')"
            ) from exc

    def find_present(self, by: str, value: str):
        """Return an element that is present in DOM (not necessarily visible)."""
        try:
            return self.wait.until(
                EC.presence_of_element_located((by, value)),
                message=f"Element not present in DOM: ({by}, '{value}')",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for element presence ({by}, '{value}')"
            ) from exc

    def type_text(self, by: str, value: str, text: str) -> None:
        """Clear a field and type text into it."""
        try:
            element = self.find(by, value)
            element.clear()
            if text:
                element.send_keys(text)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not type into element ({by}, '{value}'): {exc}"
            ) from exc

    def click(self, by: str, value: str) -> None:
        """Wait for an element to be clickable, then click it."""
        try:
            element = self.wait.until(
                EC.element_to_be_clickable((by, value)),
                message=f"Element not clickable: ({by}, '{value}')",
            )
            element.click()
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not click element ({by}, '{value}'): {exc}"
            ) from exc

    def wait_for_url_contains(self, fragment: str) -> None:
        """Block until the current URL contains *fragment*."""
        try:
            self.wait.until(
                EC.url_contains(fragment),
                message=f"URL did not contain '{fragment}' within {DEFAULT_TIMEOUT}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"URL never contained '{fragment}'. Current URL: {self.driver.current_url}"
            ) from exc

    def is_element_present(self, by: str, value: str) -> bool:
        """Return True if element appears within a short grace period."""
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def get_element_attribute(self, by: str, value: str, attribute: str) -> str:
        """Return the given attribute of a located element."""
        try:
            element = self.find_present(by, value)
            return element.get_attribute(attribute) or ""
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not read attribute '{attribute}' from ({by}, '{value}'): {exc}"
            ) from exc

    def send_tab(self, by: str, value: str) -> None:
        """Focus an element then press TAB to move focus forward."""
        try:
            element = self.find(by, value)
            element.send_keys(Keys.TAB)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not send TAB from element ({by}, '{value}'): {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# LoginPage Page Object
# ---------------------------------------------------------------------------
class LoginPage(BasePage):
    """Page object for the Login page."""

    # Locators — ordered by preference: data-testid > ARIA > CSS > XPath
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"]')

    # Validation / error message selectors
    EMAIL_ERROR = (By.CSS_SELECTOR, '[data-testid="email-error"]')
    PASSWORD_ERROR = (By.CSS_SELECTOR, '[data-testid="password-error"]')
    AUTH_ERROR = (By.CSS_SELECTOR, '[data-testid="auth-error"]')

    # Fallback ARIA / role-based locators used where data-testid is absent
    _EMAIL_ARIA = (By.XPATH, '//input[@aria-label="Email" or @name="email"]')
    _PASSWORD_ARIA = (By.XPATH, '//input[@aria-label="Password" or @name="password"]')
    # Fixed: replaced brittle contains(text()) XPath with stable data-testid CSS selector
    _SUBMIT_ARIA = (By.CSS_SELECTOR, '[data-testid="login-submit"]')

    def open(self) -> "LoginPage":
        """Navigate to the login page and return self for method chaining."""
        self.navigate(LOGIN_PATH)
        return self

    # ------------------------------------------------------------------
    # Resolved locator helpers (data-testid with ARIA fallback)
    # ------------------------------------------------------------------
    def _email_locator(self):
        return self.EMAIL_INPUT

    def _password_locator(self):
        return self.PASSWORD_INPUT

    def _submit_locator(self):
        return self.SUBMIT_BUTTON

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def enter_email(self, email: str) -> "LoginPage":
        """Type *email* into the email field (clears first)."""
        loc = self._email_locator()
        self.type_text(*loc, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Type *password* into the password field (clears first)."""
        loc = self._password_locator()
        self.type_text(*loc, password)
        return self

    def click_submit(self) -> "LoginPage":
        """Click the login / submit button."""
        self.click(*self._submit_locator())
        return self

    def login(self, email: str, password: str) -> None:
        """Full login workflow: fill form and submit."""
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()

    # ------------------------------------------------------------------
    # Queries / Assertions helpers
    # ------------------------------------------------------------------
    def is_on_dashboard(self) -> bool:
        """Return True when URL contains the dashboard path."""
        try:
            self.wait_for_url_contains(DASHBOARD_PATH)
            return True
        except TimeoutException:
            return False

    def is_on_login_page(self) -> bool:
        """Return True when URL contains the login path."""
        return LOGIN_PATH in self.driver.current_url

    def email_error_displayed(self) -> bool:
        """Return True if the email field validation error is visible."""
        return self.is_element_present(*self.EMAIL_ERROR)

    def password_error_displayed(self) -> bool:
        """Return True if the password field validation error is visible."""
        return self.is_element_present(*self.PASSWORD_ERROR)

    def auth_error_displayed(self) -> bool:
        """Return True if the authentication error banner is visible."""
        return self.is_element_present(*self.AUTH_ERROR)

    def get_password_field_type(self) -> str:
        """Return the *type* attribute of the password input element."""
        return self.get_element_attribute(*self._password_locator(), "type")

    def get_email_aria_label(self) -> str:
        """Return the aria-label of the email input."""
        return self.get_element_attribute(*self._email_locator(), "aria-label")

    def get_password_aria_label(self) -> str:
        """Return the aria-label of the password input."""
        return self.get_element_attribute(*self._password_locator(), "aria-label")

    def get_submit_aria_label(self) -> str:
        """Return the aria-label (or text) of the submit button."""
        try:
            element = self.find(*self._submit_locator())
            return element.get_attribute("aria-label") or element.text
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(f"Could not read submit button aria-label: {exc}") from exc

    def tab_through_form(self) -> None:
        """Focus email field and TAB through password → submit."""
        try:
            email_el = self.find(*self._email_locator())
            email_el.click()
            email_el.send_keys(Keys.TAB)   # email → password
            pwd_el = self.driver.switch_to.active_element
            pwd_el.send_keys(Keys.TAB)      # password → submit
        except WebDriverException as exc:
            raise RuntimeError(f"Keyboard navigation through form failed: {exc}") from exc

    def get_active_element_tag(self) -> str:
        """Return tag name of the currently focused element."""
        try:
            return self.driver.switch_to.active_element.tag_name
        except WebDriverException as exc:
            raise RuntimeError(f"Could not retrieve active element tag: {exc}") from exc

    def get_active_element_type(self) -> str:
        """Return type attribute of the currently focused element (or '')."""
        try:
            el = self.driver.switch_to.active_element
            return el.get_attribute("type") or ""
        except WebDriverException as exc:
            raise RuntimeError(f"Could not retrieve active element type: {exc}") from exc


# ---------------------------------------------------------------------------
# Fixtures  (mirror what conftest.py would expose; safe to coexist with one)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def driver():
    """
    Provide a WebDriver instance with guaranteed teardown.

    This fixture ensures driver.quit() is always called via the finally block,
    even if the test raises an exception, preventing browser process leaks.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    _driver = webdriver.Chrome(options=options)
    _driver.implicitly_wait(0)  # rely on explicit waits only
    try:
        yield _driver
    finally:
        _driver.quit()


@pytest.fixture(scope="function")
def login_page(driver):
    """Return a LoginPage instance already navigated to the login URL."""
    page = LoginPage(driver)
    page.open()
    return page


# ---------------------------------------------------------------------------
# Credentials fixture — reads from env vars to avoid hardcoded secrets
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def valid_credentials():
    """
    Return a (email, password) tuple sourced from environment variables.

    Set TEST_EMAIL and TEST_PASSWORD before running the suite:
        export TEST_EMAIL=admin@test.com
        export TEST_PASSWORD=Correct_Pass123
    """
    email = os.getenv("TEST_EMAIL", "admin@test.com")
    password = os.getenv("TEST_PASSWORD", "Correct_Pass123")
    return email, password


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@pytest.mark.regression
class TestTC001SuccessfulLogin:
    """TC_001 — Successful login with valid credentials navigates to dashboard."""

    def test_successful_login_redirects_to_dashboard(self, login_page, valid_credentials):
        """
        Verify that submitting the login form with a known-good email and
        password redirects the user to the dashboard page and that no
        inline validation errors are rendered.
        """
        email, password = valid_credentials

        login_page.login(email, password)

        assert login_page.is_on_dashboard(), (
            f"Expected redirection to '{DASHBOARD_PATH}' after valid login, "
            f"but current URL is: {login_page.driver.current_url}"
        )
        assert not login_page.email_error_displayed(), (
            "Email validation error should NOT be shown after a successful login."
        )
        assert not login_page.password_error_displayed(), (
            "Password validation error should NOT be shown after a successful login."
        )
        assert not login_page.auth_error_displayed(), (
            "Authentication error should NOT be shown after a successful login."
        )


@pytest.mark.regression
class TestTC002EmptyCredentials:
    """TC_002 — Login blocked when both email and password fields are empty."""

    def test_empty_email_and_password_shows_required_errors(self, login_page):
        """
        Verify that clicking Submit with both fields empty does NOT submit the
        form; instead, required-field validation errors are shown for both the
        email and password fields.
        """
        login_page.click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted — user must remain on login page."
        )
        assert login_page.email_error_displayed(), (
            "A required-field error MUST be displayed for the empty email field."
        )
        assert login_page.password_error_displayed(), (
            "A required-field error MUST be displayed for the empty password field."
        )


@pytest.mark.regression
class TestTC003EmptyPassword:
    """TC_003 — Login blocked when password field is left empty."""

    def test_valid_email_empty_password_shows_password_error_only(self, login_page):
        """
        Verify that entering a valid email but leaving the password field empty
        prevents form submission and shows a required-field error exclusively for
        the password field, with no error on the email field.
        """
        test_email = os.getenv("TEST_EMAIL", "admin@test.com")
        login_page.enter_email(test_email).click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted — user must remain on login page."
        )
        assert login_page.password_error_displayed(), (
            "A required-field error MUST be displayed for the empty password field."
        )
        assert not login_page.email_error_displayed(), (
            "No validation error should appear for a correctly filled email field."
        )


@pytest.mark.regression
class TestTC004EmptyEmail:
    """TC_004 — Login blocked when email field is left empty."""

    def test_empty_email_valid_password_shows_email_error_only(self, login_page):
        """
        Verify that leaving the email field empty while providing a valid password
        prevents form submission and shows a required-field error exclusively for
        the email field, with no error on the password field.
        """
        test_password = os.getenv("TEST_PASSWORD", "Correct_Pass123")
        login_page.enter_password(test_password).click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted — user must remain on login page."
        )
        assert login_page.email_error_displayed(), (
            "A required-field error MUST be displayed for the empty email field."
        )
        assert not login_page.password_error_displayed(), (
            "No validation error should appear for a correctly filled password field."
        )


@pytest.mark.regression
class TestTC005InvalidEmailFormat:
    """TC_005 — Login blocked when email address format is invalid."""

    @pytest.mark.parametrize(
        "malformed_email",
        [
            "not-an-email",
            "missing@tld",
            "@nodomain.com",
            "spaces in@email.com",
            "double@@at.com",
        ],
    )
    def test_malformed_email_shows_format_error(self, login_page, malformed_email):
        """
        Verify that entering a malformed email address (multiple variants tested)
        together with a valid password prevents form submission and displays an
        email-format validation error.
        """
        test_password = os.getenv("TEST_PASSWORD", "Correct_Pass123")
        login_page.enter_email(malformed_email)
        login_page.enter_password(test_password)
        login_page.click_submit()

        assert login_page.is_on_login_page(), (
            f"Form should NOT have been submitted for invalid email '{malformed_email}'."
        )
        assert login_page.email_error_displayed(), (
            f"An email-format validation error MUST be shown for input '{malformed_email}'."
        )


@pytest.mark.regression
class TestTC006WrongPassword:
    """TC_006 — Login blocked and error shown when credentials are incorrect."""

    def test_wrong_password_shows_auth_error_on_login_page(self, login_page):
        """
        Verify that submitting a valid email paired with an incorrect password
        keeps the user on the login page and renders an authentication error
        message (e.g. 'Invalid credentials').
        """
        test_email = os.getenv("TEST_EMAIL", "admin@test.com")
        login_page.login(test_email, "WrongPassword!")

        assert login_page.is_on_login_page(), (
            "User MUST remain on the login page after submitting wrong credentials."
        )
        assert login_page.auth_error_displayed(), (
            "An authentication error message MUST be displayed for wrong credentials."
        )


@pytest.mark.regression
class TestTC007PasswordMasking:
    """TC_007 — Password field masks input characters for security."""

    def test_password_input_type_is_password(self, login_page):
        """
        Verify that the password input element has type='password', which causes
        browsers to mask entered characters so they are not visible in plain text.
        """
        test_password = os.getenv("TEST_PASSWORD", "Correct_Pass123")
        login_page.enter_password(test_password)

        field_type = login_page.get_password_field_type()

        assert field_type == "password", (
            f"Password field type MUST be 'password' to mask input, got '{field_type}'."
        )


@pytest.mark.regression
class TestTC008KeyboardAndAriaAccessibility:
    """TC_008 — Login form is accessible via keyboard navigation and screen reader labels."""

    def test_keyboard_tab_order_traverses_email_password_submit(self, login_page):
        """
        Verify that pressing TAB from the email field moves focus to the password
        field, and a second TAB moves focus to the submit button, confirming the
        correct logical keyboard tab order for the login form.
        """
        try:
            email_el = login_page.find(*login_page._email_locator())
            email_el.click()

            # TAB from email → should land on password
            email_el.send_keys(Keys.TAB)
            active_after_first_tab = login_page.driver.switch_to.active_element
            active_type_after_first_tab = active_after_first_tab.get_attribute("type") or ""

            assert active_type_after_first_tab == "password", (
                "After TAB from email field, focus MUST move to the password field "
                f"(type='password'), but active element type was '{active_type_after_first_tab}'."
            )

            # TAB from password → should land on submit button
            active_after_first_tab.send_keys(Keys.TAB)
            active_after_second_tab = login_page.driver.switch_to.active_element
            active_tag_after_second_tab = active_after_second_tab.tag_name
            active_type_after_second_tab = active_after_second_tab.get_attribute("type") or ""

            assert active_tag_after_second_tab == "button" or active_type_after_second_tab == "submit", (
                "After TAB from password field, focus MUST move to the submit button, "
                f"but active element was <{active_tag_after_second_tab} type='{active_type_after_second_tab}'>."
            )
        except WebDriverException as exc:
            raise AssertionError(
                f"Keyboard navigation test failed due to a WebDriver error: {exc}"
            ) from exc

    def test_form_elements_have_aria_labels(self, login_page):
        """
        Verify that the email input, password input, and submit button each carry
        a non-empty aria-label or accessible text so that screen readers can
        announce the purpose of every interactive form element.
        """
        email_aria = login_page.get_email_aria_label()
        password_aria = login_page.get_password_aria_label()
        submit_aria = login_page.get_submit_aria_label()

        assert email_aria, (
            "The email input MUST have a non-empty aria-label for screen-reader accessibility."
        )
        assert password_aria, (
            "The password input MUST have a non-empty aria-label for screen-reader accessibility."
        )
        assert submit_aria, (
            "The submit button MUST have a non-empty aria-label or visible text "
            "for screen-reader accessibility."
        )