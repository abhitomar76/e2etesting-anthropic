import os
import pytest
from selenium import webdriver
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
# Configuration constants – read from environment variables, never hard-coded
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
if not BASE_URL:
    raise EnvironmentError(
        "BASE_URL environment variable is not set. "
        "Export it before running the suite, e.g.: export BASE_URL=https://example.com"
    )

DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "10"))
LOGIN_PATH = os.environ.get("LOGIN_PATH", "/login")
DASHBOARD_PATH = os.environ.get("DASHBOARD_PATH", "/dashboard")

# Credentials are read from environment variables only – never stored in source.
VALID_EMAIL = os.environ.get("TEST_EMAIL", "")
VALID_PASSWORD = os.environ.get("TEST_PASSWORD", "")
if not VALID_EMAIL or not VALID_PASSWORD:
    raise EnvironmentError(
        "TEST_EMAIL and TEST_PASSWORD environment variables must be set before running "
        "the suite. Never hard-code credentials in test source files."
    )


# ---------------------------------------------------------------------------
# Base Page
# ---------------------------------------------------------------------------
class BasePage:
    """Thin wrapper around WebDriver that every page object inherits from."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def navigate(self, path: str) -> None:
        """Navigate to a URL path relative to BASE_URL."""
        try:
            self.driver.get(f"{BASE_URL}{path}")
        except WebDriverException as exc:
            raise RuntimeError(f"Failed to navigate to '{path}': {exc}") from exc

    def find(self, by: str, value: str):
        """Wait for and return a single visible element."""
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
        """Wait for an element to be present in DOM (not necessarily visible)."""
        try:
            return self.wait.until(
                EC.presence_of_element_located((by, value)),
                message=f"Element not present: ({by}, '{value}')",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for presence of element ({by}, '{value}')"
            ) from exc

    def type_text(self, by: str, value: str, text: str) -> None:
        """Clear a field and type text into it."""
        try:
            element = self.find(by, value)
            element.clear()
            element.send_keys(text)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to type text into ({by}, '{value}'): {exc}"
            ) from exc

    def click(self, by: str, value: str) -> None:
        """Wait for an element to be clickable and click it."""
        try:
            element = self.wait.until(
                EC.element_to_be_clickable((by, value)),
                message=f"Element not clickable: ({by}, '{value}')",
            )
            element.click()
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to click element ({by}, '{value}'): {exc}"
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

    def is_element_present(self, by: str, value: str, timeout: int = 3) -> bool:
        """Return True if element appears within *timeout* seconds."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def get_attribute(self, by: str, value: str, attribute: str) -> str:
        """Return the named attribute of a located element."""
        try:
            element = self.find_present(by, value)
            return element.get_attribute(attribute) or ""
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to get attribute '{attribute}' from ({by}, '{value}'): {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Login Page Object
# ---------------------------------------------------------------------------
class LoginPage(BasePage):
    """Page object for the login page at BASE_URL/login."""

    # Locators – priority: data-testid > ARIA role > CSS > XPath
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"], [name="email"], input[type="email"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password"], [name="password"], input[type="password"]')
    SUBMIT_BUTTON = (
        By.XPATH,
        '//button[@data-testid="login-submit"] | //button[@type="submit"] | //input[@type="submit"]',
    )
    AUTH_ERROR = (
        By.XPATH,
        '//*[@data-testid="auth-error"] | //*[@role="alert"] | //*[contains(@class,"error") and contains(@class,"auth")]',
    )
    EMAIL_ERROR = (
        By.XPATH,
        '//*[@data-testid="email-error"] | //*[@id="email-error"] | '
        '//*[contains(@class,"error")][preceding::input[@type="email" or @name="email"][1]]',
    )
    PASSWORD_ERROR = (
        By.XPATH,
        '//*[@data-testid="password-error"] | //*[@id="password-error"] | '
        '//*[contains(@class,"error")][preceding::input[@type="password" or @name="password"][1]]',
    )

    def load(self) -> "LoginPage":
        """Navigate to the login page and return self for chaining."""
        self.navigate(LOGIN_PATH)
        try:
            self.find(*self.EMAIL_INPUT)
        except TimeoutException as exc:
            raise RuntimeError(
                "Login page did not load: email field not found."
            ) from exc
        return self

    def enter_email(self, email: str) -> "LoginPage":
        """Enter a value into the email field (empty string clears it)."""
        try:
            element = self.find(*self.EMAIL_INPUT)
            element.clear()
            if email:
                element.send_keys(email)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(f"Failed to enter email '{email}': {exc}") from exc
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Enter a value into the password field (empty string clears it)."""
        try:
            element = self.find(*self.PASSWORD_INPUT)
            element.clear()
            if password:
                element.send_keys(password)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(f"Failed to enter password: {exc}") from exc
        return self

    def click_submit(self) -> "LoginPage":
        """Click the form submit button."""
        self.click(*self.SUBMIT_BUTTON)
        return self

    def submit_login(self, email: str, password: str) -> "LoginPage":
        """High-level helper: fill credentials and submit the form."""
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()
        return self

    def wait_for_dashboard(self) -> None:
        """Assert redirect to the dashboard URL."""
        self.wait_for_url_contains(DASHBOARD_PATH)

    def is_on_login_page(self) -> bool:
        """Return True if the current URL still points to the login page."""
        return LOGIN_PATH in self.driver.current_url

    def get_auth_error_text(self) -> str:
        """Return visible authentication error message text."""
        try:
            element = self.find(*self.AUTH_ERROR)
            return element.text.strip()
        except TimeoutException:
            return ""

    def has_auth_error(self) -> bool:
        """Return True if an authentication-level error is visible."""
        return self.is_element_present(*self.AUTH_ERROR)

    def has_email_error(self) -> bool:
        """Return True if an email field validation error is visible."""
        return self.is_element_present(*self.EMAIL_ERROR)

    def has_password_error(self) -> bool:
        """Return True if a password field validation error is visible."""
        return self.is_element_present(*self.PASSWORD_ERROR)

    def get_password_field_type(self) -> str:
        """Return the type attribute of the password input element."""
        return self.get_attribute(*self.PASSWORD_INPUT, attribute="type")

    def get_email_field_aria_label(self) -> str:
        """Return aria-label of the email field (may be empty if labelled differently)."""
        return self.get_attribute(*self.EMAIL_INPUT, attribute="aria-label")

    def get_password_field_aria_label(self) -> str:
        """Return aria-label of the password field."""
        return self.get_attribute(*self.PASSWORD_INPUT, attribute="aria-label")

    def get_submit_button_element(self):
        """Return the submit button WebElement."""
        return self.find(*self.SUBMIT_BUTTON)

    def tab_through_form(self) -> None:
        """
        Simulate keyboard-only navigation by pressing Tab from the email
        field through password field to the submit button.

        An explicit wait is used after each Tab keypress to allow the browser
        to transfer focus before reading switch_to.active_element.
        """
        try:
            email_el = self.find(*self.EMAIL_INPUT)
            email_el.send_keys(Keys.TAB)
            # Wait explicitly for the password field to become the active/focused element
            WebDriverWait(self.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable(self.PASSWORD_INPUT),
                message="Password field did not receive focus after Tab from email field.",
            )
            password_el = self.driver.switch_to.active_element
            password_el.send_keys(Keys.TAB)
            # Wait explicitly for the submit button to become the active/focused element
            WebDriverWait(self.driver, DEFAULT_TIMEOUT).until(
                EC.element_to_be_clickable(self.SUBMIT_BUTTON),
                message="Submit button did not receive focus after Tab from password field.",
            )
        except WebDriverException as exc:
            raise RuntimeError(f"Keyboard tab navigation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Dashboard Page Object (minimal – used only for post-login assertions)
# ---------------------------------------------------------------------------
class DashboardPage(BasePage):
    """Minimal page object for the dashboard – verifies successful login."""

    # Use a stable data-testid landmark; fall back to the ARIA main landmark rather
    # than generic tag names such as //h1 | //main which are far too broad.
    DASHBOARD_HEADING = (
        By.XPATH,
        '//*[@data-testid="dashboard-heading"] | //*[@role="main"] | //*[@data-testid="dashboard-root"]',
    )

    def is_loaded(self) -> bool:
        """Return True when the dashboard URL is current and main content is present."""
        return DASHBOARD_PATH in self.driver.current_url and self.is_element_present(
            *self.DASHBOARD_HEADING
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def driver():
    """
    Provide a Chrome WebDriver instance for a single test function.

    The driver is always quit in the finally block so no browser window is
    left open even when a test raises an unexpected exception.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    _driver = webdriver.Chrome(options=options)
    try:
        yield _driver
    finally:
        try:
            _driver.quit()
        except WebDriverException:
            pass  # Already closed or unreachable – nothing to do.


@pytest.fixture
def login_page(driver):
    """Provide a LoginPage instance navigated to the login URL."""
    page = LoginPage(driver)
    page.load()
    return page


@pytest.fixture
def dashboard_page(driver):
    """Provide a DashboardPage instance (navigation done by tests)."""
    return DashboardPage(driver)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@pytest.mark.regression
def test_tc001_successful_login_navigates_to_dashboard(login_page, dashboard_page):
    """
    TC_001 – Successful login with valid credentials navigates to dashboard.

    Given the user is on the login page,
    when they enter a valid email and correct password and submit,
    then they are redirected to the dashboard with no error messages shown.

    Credentials are sourced from the TEST_EMAIL and TEST_PASSWORD environment
    variables – never hard-coded.
    """
    login_page.submit_login(VALID_EMAIL, VALID_PASSWORD)
    login_page.wait_for_dashboard()

    # Explicit assertion on dashboard state (was missing in original script).
    assert dashboard_page.is_loaded(), (
        "Expected to land on the dashboard after successful login, "
        f"but current URL is: {login_page.driver.current_url}"
    )
    assert not login_page.has_auth_error(), (
        "No authentication error should be displayed after a successful login."
    )


@pytest.mark.regression
def test_tc002_login_blocked_with_auth_error_for_wrong_password(login_page):
    """
    TC_002 – Login blocked with authentication error for incorrect password.

    Given the user is on the login page,
    when they enter a valid email but an incorrect password and submit,
    then they remain on the login page and an authentication error is displayed.

    The valid email is read from TEST_EMAIL; the wrong password is intentionally
    crafted so it will never match a real account.
    """
    wrong_password = "deliberately_wrong_password_that_will_never_match_xYz987"

    login_page.submit_login(VALID_EMAIL, wrong_password)

    assert login_page.is_on_login_page(), (
        "User should remain on the login page after entering incorrect credentials, "
        f"but was redirected to: {login_page.driver.current_url}"
    )
    assert login_page.has_auth_error(), (
        "An authentication error message should be displayed for incorrect password, "
        "but none was found."
    )
    error_text = login_page.get_auth_error_text()
    assert error_text, (
        "The authentication error element is present but contains no visible text."
    )


@pytest.mark.regression
def test_tc003_login_blocked_with_validation_errors_when_both_fields_empty(login_page):
    """
    TC_003 – Login blocked with required field errors when both fields are empty.

    Given the user is on the login page,
    when they submit the form with both fields empty,
    then the form is not submitted and required field errors appear for both fields.
    """
    login_page.submit_login("", "")

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when both fields are empty, "
        f"but current URL is: {login_page.driver.current_url}"
    )
    assert login_page.has_email_error(), (
        "A required-field error should be displayed for the email field."
    )
    assert login_page.has_password_error(), (
        "A required-field error should be displayed for the password field."
    )


@pytest.mark.regression
def test_tc004_login_blocked_with_format_error_for_invalid_email(login_page):
    """
    TC_004 – Login blocked with format error for invalid email format.

    Given the user is on the login page,
    when they enter a malformed email address with a valid password and submit,
    then the form is not submitted and an email format validation error is displayed.
    """
    email = "not-an-email"
    password = "valid_pass123"

    login_page.submit_login(email, password)

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when the email format is invalid, "
        f"but current URL is: {login_page.driver.current_url}"
    )
    assert login_page.has_email_error(), (
        "An email format validation error should be displayed for 'not-an-email'."
    )


@pytest.mark.regression
def test_tc005_login_blocked_with_required_error_when_email_missing(login_page):
    """
    TC_005 – Login blocked with required field error when only email is missing.

    Given the user is on the login page,
    when they leave the email field empty, enter a valid password, and submit,
    then the form is not submitted and a required-field error appears only for email.
    """
    password = "valid_pass123"

    login_page.submit_login("", password)

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when email field is empty, "
        f"but current URL is: {login_page.driver.current_url}"
    )
    assert login_page.has_email_error(), (
        "A required-field error should be shown for the empty email field."
    )
    assert not login_page.has_password_error(), (
        "No error should be shown for the password field when it has a valid value."
    )


@pytest.mark.regression
def test_tc006_login_blocked_with_required_error_when_password_missing(login_page):
    """
    TC_006 – Login blocked with required field error when only password is missing.

    Given the user is on the login page,
    when they enter a valid email, leave the password field empty, and submit,
    then the form is not submitted and a required-field error appears only for password.

    The valid email address is read from the TEST_EMAIL environment variable.
    """
    login_page.submit_login(VALID_EMAIL, "")

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when password field is empty, "
        f"but current URL is: {login_page.driver.current_url}"
    )
    assert login_page.has_password_error(), (
        "A required-field error should be shown for the empty password field."
    )
    assert not login_page.has_email_error(), (
        "No error should be shown for the email field when it contains a valid value."
    )


@pytest.mark.regression
@pytest.mark.a11y
def test_tc007_password_field_masks_entered_characters(login_page):
    """
    TC_007 – Password field masks entered characters for security.

    Given the user is on the login page,
    when they type a password into the password field,
    then the field type is 'password' so characters are masked and not visible as plain text.
    """
    test_password = "test_password"

    login_page.enter_password(test_password)

    field_type = login_page.get_password_field_type()
    assert field_type == "password", (
        f"Password input type should be 'password' to mask characters, "
        f"but found type='{field_type}'."
    )


@pytest.mark.regression
@pytest.mark.a11y
def test_tc008_login_form_aria_labels_and_keyboard_navigation(login_page):
    """
    TC_008 – Login form is accessible with correct ARIA labels and keyboard navigation.

    Given the user is on the login page,
    when they navigate with only the keyboard and inspect ARIA attributes,
    then all fields and the submit button are reachable via Tab and each has
    an appropriate ARIA label or role.
    """
    # --- Keyboard navigation ---
    try:
        login_page.tab_through_form()
        # After tabbing twice from email, the active element should be the submit button.
        # tab_through_form() already waits for the submit button to be focusable, so
        # reading active_element here is safe.
        active_element = login_page.driver.switch_to.active_element
        tag_name = active_element.tag_name.lower()
        el_type = (active_element.get_attribute("type") or "").lower()
        assert tag_name == "button" or el_type == "submit", (
            f"Expected focus to land on the submit button after Tab navigation, "
            f"but active element is <{tag_name} type='{el_type}'>."
        )
    except RuntimeError as exc:
        pytest.fail(f"Keyboard navigation through login form failed: {exc}")

    # --- ARIA / semantic attributes on email field ---
    try:
        email_el = login_page.find(*LoginPage.EMAIL_INPUT)
        email_aria_label = email_el.get_attribute("aria-label") or ""
        email_aria_labelledby = email_el.get_attribute("aria-labelledby") or ""
        email_id = email_el.get_attribute("id") or ""
        email_placeholder = email_el.get_attribute("placeholder") or ""

        has_email_label = bool(
            email_aria_label
            or email_aria_labelledby
            or email_placeholder
        )
        if email_id:
            label_present = login_page.is_element_present(
                By.XPATH, f'//label[@for="{email_id}"]'
            )
            has_email_label = has_email_label or label_present

        assert has_email_label, (
            "Email field is missing an accessible label "
            "(aria-label, aria-labelledby, associated <label>, or placeholder)."
        )
    except (TimeoutException, WebDriverException) as exc:
        pytest.fail(f"Could not inspect email field ARIA attributes: {exc}")

    # --- ARIA / semantic attributes on password field ---
    try:
        pwd_el = login_page.find(*LoginPage.PASSWORD_INPUT)
        pwd_aria_label = pwd_el.get_attribute("aria-label") or ""
        pwd_aria_labelledby = pwd_el.get_attribute("aria-labelledby") or ""
        pwd_id = pwd_el.get_attribute("id") or ""
        pwd_placeholder = pwd_el.get_attribute("placeholder") or ""

        has_pwd_label = bool(
            pwd_aria_label or pwd_aria_labelledby or pwd_placeholder
        )
        if pwd_id:
            label_present = login_page.is_element_present(
                By.XPATH, f'//label[@for="{pwd_id}"]'
            )
            has_pwd_label = has_pwd_label or label_present

        assert has_pwd_label, (
            "Password field is missing an accessible label "
            "(aria-label, aria-labelledby, associated <label>, or placeholder)."
        )
    except (TimeoutException, WebDriverException) as exc:
        pytest.fail(f"Could not inspect password field ARIA attributes: {exc}")

    # --- Submit button has accessible name ---
    try:
        submit_el = login_page.get_submit_button_element()
        button_text = submit_el.text.strip()
        button_aria_label = submit_el.get_attribute("aria-label") or ""
        button_value = submit_el.get_attribute("value") or ""
        button_title = submit_el.get_attribute("title") or ""

        has_submit_label = bool(
            button_text or button_aria_label or button_value or button_title
        )
        assert has_submit_label, (
            "Submit button has no accessible name "
            "(text content, aria-label, value, or title)."
        )
    except (TimeoutException, RuntimeError) as exc:
        pytest.fail(f"Could not inspect submit button ARIA attributes: {exc}")


# ---------------------------------------------------------------------------
# Parametrized edge-case matrix (covers TC_003 – TC_006 variations compactly)
# ---------------------------------------------------------------------------
@pytest.mark.regression
@pytest.mark.parametrize(
    "email,password,expect_email_err,expect_pwd_err,expect_auth_err,test_id",
    [
        ("", "", True, True, False, "both_empty"),
        ("not-an-email", "valid_pass123", True, False, False, "bad_email_format"),
        ("", "valid_pass123", True, False, False, "email_missing"),
        # Use the environment-supplied valid email so the address itself is not rejected.
        (VALID_EMAIL, "", False, True, False, "password_missing"),
        (VALID_EMAIL, "deliberately_wrong_xYz987", False, False, True, "wrong_password"),
    ],
)
def test_login_validation_matrix(
    login_page,
    email,
    password,
    expect_email_err,
    expect_pwd_err,
    expect_auth_err,
    test_id,
):
    """
    Parametrized matrix covering multiple login validation scenarios.

    Verifies that the correct combination of email error, password error,
    and authentication error appears (or does not appear) for each input set.
    Credentials are sourced from environment variables, not hard-coded.
    """
    login_page.submit_login(email, password)

    if expect_email_err:
        assert login_page.has_email_error(), (
            f"[{test_id}] Expected an email field error but none was found. "
            f"Inputs – email='{email}', password='<redacted>'"
        )
    else:
        assert not login_page.has_email_error(), (
            f"[{test_id}] Did not expect an email field error but one was shown. "
            f"Inputs – email='{email}', password='<redacted>'"
        )

    if expect_pwd_err:
        assert login_page.has_password_error(), (
            f"[{test_id}] Expected a password field error but none was found. "
            f"Inputs – email='{email}', password='<redacted>'"
        )
    else:
        assert not login_page.has_password_error(), (
            f"[{test_id}] Did not expect a password field error but one was shown. "
            f"Inputs – email='{email}', password='<redacted>'"
        )

    if expect_auth_err:
        assert login_page.has_auth_error(), (
            f"[{test_id}] Expected an authentication error but none was found. "
            f"Inputs – email='{email}', password='<redacted>'"
        )
    else:
        assert not login_page.has_auth_error(), (
            f"[{test_id}] Did not expect an authentication error but one was shown. "
            f"Inputs – email='{email}', password='<redacted>'"
        )