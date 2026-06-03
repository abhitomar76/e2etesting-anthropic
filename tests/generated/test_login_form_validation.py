import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# ---------------------------------------------------------------------------
# Configuration constants (mirrors what conftest.py would expose)
# ---------------------------------------------------------------------------
BASE_URL = "https://www.google.com"
DEFAULT_TIMEOUT = 10
LOGIN_PATH = "/login"
DASHBOARD_PATH = "/dashboard"


# ---------------------------------------------------------------------------
# Base Page
# ---------------------------------------------------------------------------
class BasePage:
    """Provides shared driver helpers for all page objects."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def navigate(self, path: str) -> None:
        """Navigate to BASE_URL + path."""
        try:
            self.driver.get(f"{BASE_URL}{path}")
        except WebDriverException as exc:
            raise RuntimeError(f"Failed to navigate to '{path}': {exc}") from exc

    def find(self, by: str, locator: str):
        """Wait for and return a visible element."""
        try:
            return self.wait.until(
                EC.visibility_of_element_located((by, locator)),
                message=f"Element not visible: ({by}, '{locator}')",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for element ({by}, '{locator}')"
            ) from exc

    def find_present(self, by: str, locator: str):
        """Wait for element presence in DOM (not necessarily visible)."""
        try:
            return self.wait.until(
                EC.presence_of_element_located((by, locator)),
                message=f"Element not present: ({by}, '{locator}')",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for presence of ({by}, '{locator}')"
            ) from exc

    def type_text(self, by: str, locator: str, text: str) -> None:
        """Clear an input and type text into it."""
        try:
            element = self.find(by, locator)
            element.clear()
            if text:
                element.send_keys(text)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to type into ({by}, '{locator}'): {exc}"
            ) from exc

    def click(self, by: str, locator: str) -> None:
        """Wait for element to be clickable then click it."""
        try:
            element = self.wait.until(
                EC.element_to_be_clickable((by, locator)),
                message=f"Element not clickable: ({by}, '{locator}')",
            )
            element.click()
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to click ({by}, '{locator}'): {exc}"
            ) from exc

    def wait_for_url_contains(self, partial_url: str) -> None:
        """Block until the current URL contains partial_url."""
        try:
            self.wait.until(
                EC.url_contains(partial_url),
                message=f"URL did not contain '{partial_url}' within {DEFAULT_TIMEOUT}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"URL never contained '{partial_url}'. Current URL: {self.driver.current_url}"
            ) from exc

    def is_element_present(self, by: str, locator: str) -> bool:
        """Return True if element is present in DOM within a short wait."""
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((by, locator))
            )
            return True
        except TimeoutException:
            return False

    def get_element_attribute(self, by: str, locator: str, attribute: str) -> str:
        """Return the value of a DOM attribute on a located element."""
        try:
            element = self.find_present(by, locator)
            return element.get_attribute(attribute) or ""
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to get attribute '{attribute}' from ({by}, '{locator}'): {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Login Page Object
# ---------------------------------------------------------------------------
class LoginPage(BasePage):
    """Page object for the Login page."""

    # Locators — prefer data-testid, fall back to ARIA/CSS/XPath
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"]')

    # Validation / error message locators
    EMAIL_ERROR = (By.CSS_SELECTOR, '[data-testid="email-error"]')
    PASSWORD_ERROR = (By.CSS_SELECTOR, '[data-testid="password-error"]')
    GENERAL_ERROR = (By.CSS_SELECTOR, '[data-testid="login-error"]')

    # Fallback ARIA/CSS locators used if data-testid is absent
    _EMAIL_INPUT_FALLBACK = (By.XPATH, '//input[@type="email" or @name="email" or @id="email"]')
    _PASSWORD_INPUT_FALLBACK = (By.XPATH, '//input[@type="password"]')
    _SUBMIT_FALLBACK = (
        By.XPATH,
        '//button[@type="submit" or contains(translate(text(),"LOGIN","login"),"login")]',
    )
    _EMAIL_ERROR_FALLBACK = (By.XPATH, '//*[contains(@class,"error") and contains(@class,"email")]')
    _PASSWORD_ERROR_FALLBACK = (
        By.XPATH,
        '//*[contains(@class,"error") and contains(@class,"password")]',
    )
    _GENERAL_ERROR_FALLBACK = (
        By.XPATH,
        '//*[contains(@class,"alert") or contains(@class,"error-message")]'
        '[contains(text(),"Invalid credentials") or contains(text(),"invalid")]',
    )

    def _resolve_locator(self, primary, fallback):
        """Return primary locator if present in DOM, otherwise fallback."""
        if self.is_element_present(*primary):
            return primary
        return fallback

    def open(self) -> "LoginPage":
        """Navigate to the login page."""
        self.navigate(LOGIN_PATH)
        return self

    def enter_email(self, email: str) -> "LoginPage":
        """Type email into the email field."""
        locator = self._resolve_locator(self.EMAIL_INPUT, self._EMAIL_INPUT_FALLBACK)
        self.type_text(*locator, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Type password into the password field."""
        locator = self._resolve_locator(self.PASSWORD_INPUT, self._PASSWORD_INPUT_FALLBACK)
        self.type_text(*locator, password)
        return self

    def click_submit(self) -> "LoginPage":
        """Click the login / submit button."""
        locator = self._resolve_locator(self.SUBMIT_BUTTON, self._SUBMIT_FALLBACK)
        self.click(*locator)
        return self

    def login(self, email: str, password: str) -> None:
        """Full login flow: fill form and submit."""
        self.open()
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def is_on_dashboard(self) -> bool:
        """Return True when redirected to the dashboard URL."""
        try:
            self.wait_for_url_contains(DASHBOARD_PATH)
            return True
        except TimeoutException:
            return False

    def is_on_login_page(self) -> bool:
        """Return True when still on the login page."""
        return LOGIN_PATH in self.driver.current_url

    def get_email_error_text(self) -> str:
        """Return visible validation error text for the email field."""
        locator = self._resolve_locator(self.EMAIL_ERROR, self._EMAIL_ERROR_FALLBACK)
        try:
            element = self.find(locator[0], locator[1])
            return element.text
        except TimeoutException:
            return ""

    def get_password_error_text(self) -> str:
        """Return visible validation error text for the password field."""
        locator = self._resolve_locator(self.PASSWORD_ERROR, self._PASSWORD_ERROR_FALLBACK)
        try:
            element = self.find(locator[0], locator[1])
            return element.text
        except TimeoutException:
            return ""

    def get_general_error_text(self) -> str:
        """Return visible general/server-side error message text."""
        locator = self._resolve_locator(self.GENERAL_ERROR, self._GENERAL_ERROR_FALLBACK)
        try:
            element = self.find(locator[0], locator[1])
            return element.text
        except TimeoutException:
            return ""

    def has_email_validation_error(self) -> bool:
        """Return True when an email validation error is displayed."""
        return bool(self.get_email_error_text())

    def has_password_validation_error(self) -> bool:
        """Return True when a password validation error is displayed."""
        return bool(self.get_password_error_text())

    def has_invalid_credentials_error(self) -> bool:
        """Return True when the 'Invalid credentials' server error is shown."""
        general = self.get_general_error_text().lower()
        return "invalid" in general or "credentials" in general

    def get_password_field_type(self) -> str:
        """Return the 'type' attribute value of the password input element."""
        locator = self._resolve_locator(self.PASSWORD_INPUT, self._PASSWORD_INPUT_FALLBACK)
        return self.get_element_attribute(locator[0], locator[1], "type")

    def is_email_field_invalid(self) -> bool:
        """
        Return True when the browser marks the email input as invalid via the
        HTML5 Constraint Validation API (validity.valid == false).
        """
        locator = self._resolve_locator(self.EMAIL_INPUT, self._EMAIL_INPUT_FALLBACK)
        try:
            element = self.find_present(*locator)
            result = self.driver.execute_script(
                "return arguments[0].validity && !arguments[0].validity.valid;", element
            )
            return bool(result)
        except WebDriverException:
            return False

    def is_password_field_invalid(self) -> bool:
        """
        Return True when the browser marks the password input as invalid via
        the HTML5 Constraint Validation API.
        """
        locator = self._resolve_locator(self.PASSWORD_INPUT, self._PASSWORD_INPUT_FALLBACK)
        try:
            element = self.find_present(*locator)
            result = self.driver.execute_script(
                "return arguments[0].validity && !arguments[0].validity.valid;", element
            )
            return bool(result)
        except WebDriverException:
            return False


# ---------------------------------------------------------------------------
# Dashboard Page Object (minimal — only what tests need)
# ---------------------------------------------------------------------------
class DashboardPage(BasePage):
    """Page object for the Dashboard page."""

    ERROR_BANNER = (By.CSS_SELECTOR, '[data-testid="error-banner"]')
    _ERROR_BANNER_FALLBACK = (
        By.XPATH,
        '//*[contains(@class,"alert-danger") or contains(@class,"error-banner")]',
    )

    def is_loaded(self) -> bool:
        """Return True when the dashboard URL is active."""
        try:
            self.wait_for_url_contains(DASHBOARD_PATH)
            return True
        except TimeoutException:
            return False

    def has_error_message(self) -> bool:
        """Return True when any error banner/message is visible on the dashboard."""
        locator = (
            self.ERROR_BANNER
            if self.is_element_present(*self.ERROR_BANNER)
            else self._ERROR_BANNER_FALLBACK
        )
        return self.is_element_present(*locator)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def login_page(driver):
    """Provide a LoginPage instance that has already opened the login URL."""
    page = LoginPage(driver)
    page.open()
    return page


@pytest.fixture
def dashboard_page(driver):
    """Provide a DashboardPage instance (driver already on dashboard)."""
    return DashboardPage(driver)


# ---------------------------------------------------------------------------
# TC_001 – Successful login with valid credentials navigates to dashboard
# ---------------------------------------------------------------------------
@pytest.mark.smoke
@pytest.mark.regression
class TestTC001SuccessfulLogin:
    def test_valid_login_redirects_to_dashboard(self, login_page, dashboard_page):
        """
        TC_001 – Verify that submitting valid credentials redirects the user to
        the dashboard URL and that no error messages are displayed on the
        resulting page.
        """
        email = "admin@test.com"
        password = "correct_pass"

        login_page.enter_email(email)
        login_page.enter_password(password)
        login_page.click_submit()

        assert dashboard_page.is_loaded(), (
            f"Expected redirection to '{DASHBOARD_PATH}' after valid login, "
            f"but current URL is: {login_page.driver.current_url}"
        )
        assert not dashboard_page.has_error_message(), (
            "No error messages should be displayed on the dashboard after a successful login."
        )


# ---------------------------------------------------------------------------
# TC_002 – Login blocked when email field is left empty
# ---------------------------------------------------------------------------
@pytest.mark.regression
class TestTC002EmptyEmail:
    def test_empty_email_shows_validation_error(self, login_page):
        """
        TC_002 – Verify that submitting the login form with an empty email field
        prevents form submission and displays a required-field validation error
        for the email input.
        """
        login_page.enter_email("")
        login_page.enter_password("any_password")
        login_page.click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted — user must remain on the login page."
        )
        assert login_page.has_email_validation_error() or login_page.is_email_field_invalid(), (
            "A required-field validation error must be shown for the email field."
        )


# ---------------------------------------------------------------------------
# TC_003 – Login blocked when password field is left empty
# ---------------------------------------------------------------------------
@pytest.mark.regression
class TestTC003EmptyPassword:
    def test_empty_password_shows_validation_error(self, login_page):
        """
        TC_003 – Verify that submitting the login form with an empty password
        field prevents form submission and displays a required-field validation
        error for the password input.
        """
        login_page.enter_email("admin@test.com")
        login_page.enter_password("")
        login_page.click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted — user must remain on the login page."
        )
        assert (
            login_page.has_password_validation_error() or login_page.is_password_field_invalid()
        ), "A required-field validation error must be shown for the password field."


# ---------------------------------------------------------------------------
# TC_004 & TC_005 – Login blocked for invalid / non-existent credentials
# ---------------------------------------------------------------------------
@pytest.mark.regression
@pytest.mark.parametrize(
    "test_id,email,password",
    [
        ("TC_004_wrong_password", "admin@test.com", "wrong_pass"),
        ("TC_005_nonexistent_user", "nonexistent@test.com", "any_password"),
    ],
)
def test_invalid_credentials_shows_error(driver, test_id, email, password):
    """
    TC_004 / TC_005 – Verify that submitting with incorrect password or a
    non-existent account keeps the user on the login page and displays an
    'Invalid credentials' error message.

    Parameterised to cover both wrong-password and unknown-user scenarios.
    """
    page = LoginPage(driver)
    page.login(email, password)

    assert page.is_on_login_page(), (
        f"[{test_id}] User should remain on the login page after invalid login attempt, "
        f"but current URL is: {driver.current_url}"
    )
    assert page.has_invalid_credentials_error(), (
        f"[{test_id}] Expected 'Invalid credentials' error message to be displayed, "
        f"but got: '{page.get_general_error_text()}'"
    )


# ---------------------------------------------------------------------------
# TC_006 – Login blocked when email format is invalid
# ---------------------------------------------------------------------------
@pytest.mark.regression
class TestTC006InvalidEmailFormat:
    def test_malformed_email_shows_format_error(self, login_page):
        """
        TC_006 – Verify that entering a malformed email address (e.g. 'not-an-email')
        prevents form submission and causes an email-format validation error to be
        displayed (either via browser native constraint validation or application UI).
        """
        login_page.enter_email("not-an-email")
        login_page.enter_password("any_password")
        login_page.click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted for a malformed email — "
            f"but current URL is: {login_page.driver.current_url}"
        )
        email_invalid = (
            login_page.has_email_validation_error() or login_page.is_email_field_invalid()
        )
        assert email_invalid, (
            "An email format validation error must be shown for 'not-an-email'."
        )


# ---------------------------------------------------------------------------
# TC_007 – Login blocked when both fields are empty
# ---------------------------------------------------------------------------
@pytest.mark.regression
class TestTC007BothFieldsEmpty:
    def test_both_fields_empty_shows_validation_errors(self, login_page):
        """
        TC_007 – Verify that submitting the login form with both email and password
        fields empty prevents submission and shows required-field validation errors
        on both fields simultaneously.
        """
        login_page.enter_email("")
        login_page.enter_password("")
        login_page.click_submit()

        assert login_page.is_on_login_page(), (
            "Form should NOT have been submitted when both fields are empty — "
            f"but current URL is: {login_page.driver.current_url}"
        )
        email_error = (
            login_page.has_email_validation_error() or login_page.is_email_field_invalid()
        )
        password_error = (
            login_page.has_password_validation_error() or login_page.is_password_field_invalid()
        )
        assert email_error, "A required-field validation error must be shown for the email field."
        assert password_error, (
            "A required-field validation error must be shown for the password field."
        )


# ---------------------------------------------------------------------------
# TC_008 – Password field masks characters for security
# ---------------------------------------------------------------------------
@pytest.mark.regression
class TestTC008PasswordMasking:
    def test_password_field_masks_input(self, login_page):
        """
        TC_008 – Verify that the password input field has type='password', which
        causes the browser to mask entered characters so they are not displayed
        in plain text to the user.
        """
        login_page.enter_password("SecurePass123")

        field_type = login_page.get_password_field_type()
        assert field_type == "password", (
            f"Password field must have type='password' to mask characters, "
            f"but actual type attribute is: '{field_type}'"
        )