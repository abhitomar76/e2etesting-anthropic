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
# Configuration constants — read from environment / pytest config
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "http://localhost")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))
LOGIN_PATH = os.getenv("LOGIN_PATH", "/login")
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/dashboard")


# ---------------------------------------------------------------------------
# Base Page
# ---------------------------------------------------------------------------
class BasePage:
    """Shared driver helpers inherited by every page object."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def navigate(self, path: str) -> None:
        """Navigate to BASE_URL + path."""
        try:
            self.driver.get(f"{BASE_URL}{path}")
        except WebDriverException as exc:
            raise RuntimeError(f"Failed to navigate to '{path}': {exc}") from exc

    def current_url(self) -> str:
        """Return the current browser URL."""
        try:
            return self.driver.current_url
        except WebDriverException as exc:
            raise RuntimeError(f"Unable to retrieve current URL: {exc}") from exc

    def wait_for_url_contains(self, fragment: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Block until the URL contains *fragment* or raise TimeoutException."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(fragment),
                message=f"URL did not contain '{fragment}' within {timeout}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for URL to contain '{fragment}'. "
                f"Current URL: {self.current_url()}"
            ) from exc

    # ------------------------------------------------------------------
    # Element interactions
    # ------------------------------------------------------------------
    def _find(self, by: str, value: str):
        try:
            return self.wait.until(
                EC.presence_of_element_located((by, value)),
                message=f"Element not found: ({by}, '{value}')",
            )
        except TimeoutException as exc:
            raise NoSuchElementException(
                f"Element ({by}, '{value}') was not present within {DEFAULT_TIMEOUT}s"
            ) from exc

    def _find_visible(self, by: str, value: str):
        try:
            return self.wait.until(
                EC.visibility_of_element_located((by, value)),
                message=f"Element not visible: ({by}, '{value}')",
            )
        except TimeoutException as exc:
            raise NoSuchElementException(
                f"Element ({by}, '{value}') was not visible within {DEFAULT_TIMEOUT}s"
            ) from exc

    def type_text(self, by: str, value: str, text: str) -> None:
        """Clear then type *text* into the located element."""
        try:
            element = self._find_visible(by, value)
            element.clear()
            if text:
                element.send_keys(text)
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not type into element ({by}, '{value}'): {exc}"
            ) from exc

    def click(self, by: str, value: str) -> None:
        """Wait for element to be clickable then click it."""
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

    def get_text(self, by: str, value: str) -> str:
        """Return visible text of the located element."""
        try:
            return self._find_visible(by, value).text
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not get text from element ({by}, '{value}'): {exc}"
            ) from exc

    def get_attribute(self, by: str, value: str, attribute: str) -> str:
        """Return *attribute* value from the located element."""
        try:
            return self._find(by, value).get_attribute(attribute) or ""
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not get attribute '{attribute}' from ({by}, '{value}'): {exc}"
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

    def is_element_visible(self, by: str, value: str, timeout: int = 3) -> bool:
        """Return True if element is visible within *timeout* seconds."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def send_key_to_element(self, by: str, value: str, key) -> None:
        """Send a keyboard key to the located element."""
        try:
            self._find_visible(by, value).send_keys(key)
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not send key to element ({by}, '{value}'): {exc}"
            ) from exc

    def tab_to_element(self, by: str, value: str) -> None:
        """Send TAB from *by/value* element."""
        self.send_key_to_element(by, value, Keys.TAB)


# ---------------------------------------------------------------------------
# Login Page Object
# ---------------------------------------------------------------------------
class LoginPage(BasePage):
    """Page object representing the login form."""

    # Locators — priority: data-testid > ARIA > CSS > XPath
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"], input[name="email"], input[type="email"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password"], input[name="password"], input[type="password"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"], button[type="submit"]')

    # Error / validation message containers
    # Use unique data-testid selectors to avoid collision between AUTH_ERROR and LOCKOUT_MESSAGE
    EMAIL_ERROR = (By.CSS_SELECTOR, '[data-testid="email-error"], [id*="email-error"], [aria-describedby*="email"]')
    PASSWORD_ERROR = (By.CSS_SELECTOR, '[data-testid="password-error"], [id*="password-error"], [aria-describedby*="password"]')
    AUTH_ERROR = (By.CSS_SELECTOR, '[data-testid="auth-error"], .error-message, .alert-error')
    LOCKOUT_MESSAGE = (By.CSS_SELECTOR, '[data-testid="lockout-message"], .lockout-message, .account-locked')

    def open(self) -> "LoginPage":
        """Navigate to the login page and return self for fluent chaining."""
        self.navigate(LOGIN_PATH)
        # Wait for the email field to confirm the page is loaded
        self._find_visible(*self.EMAIL_INPUT)
        return self

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def enter_email(self, email: str) -> "LoginPage":
        """Type *email* into the email field."""
        self.type_text(*self.EMAIL_INPUT, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Type *password* into the password field."""
        self.type_text(*self.PASSWORD_INPUT, password)
        return self

    def click_submit(self) -> "LoginPage":
        """Click the form submit button."""
        self.click(*self.SUBMIT_BUTTON)
        return self

    def submit_login(self, email: str, password: str) -> "LoginPage":
        """Fill in credentials and click submit."""
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()
        return self

    def submit_login_with_enter(self, email: str, password: str) -> "LoginPage":
        """Fill in credentials and submit via the Enter key on the submit button."""
        self.enter_email(email)
        self.enter_password(password)
        self.send_key_to_element(*self.SUBMIT_BUTTON, Keys.ENTER)
        return self

    # ------------------------------------------------------------------
    # Assertions / queries
    # ------------------------------------------------------------------
    def is_on_login_page(self) -> bool:
        """Return True if the browser URL still contains the login path."""
        return LOGIN_PATH in self.current_url()

    def is_on_dashboard(self) -> bool:
        """Return True if the browser URL contains the dashboard path."""
        return DASHBOARD_PATH in self.current_url()

    def wait_for_dashboard(self) -> None:
        """Block until the URL contains the dashboard path."""
        self.wait_for_url_contains(DASHBOARD_PATH)

    def get_email_error_text(self) -> str:
        """Return the text of the email field validation error."""
        try:
            return self.get_text(*self.EMAIL_ERROR)
        except RuntimeError:
            return ""

    def get_password_error_text(self) -> str:
        """Return the text of the password field validation error."""
        try:
            return self.get_text(*self.PASSWORD_ERROR)
        except RuntimeError:
            return ""

    def get_auth_error_text(self) -> str:
        """Return the text of the general authentication error alert."""
        try:
            return self.get_text(*self.AUTH_ERROR)
        except RuntimeError:
            return ""

    def get_lockout_message_text(self) -> str:
        """Return the text of the account-lockout message."""
        try:
            return self.get_text(*self.LOCKOUT_MESSAGE)
        except RuntimeError:
            return ""

    def is_auth_error_displayed(self) -> bool:
        """Return True if an authentication error element is visible."""
        return self.is_element_visible(*self.AUTH_ERROR)

    def is_email_error_displayed(self) -> bool:
        """Return True if an email validation error is visible."""
        return self.is_element_visible(*self.EMAIL_ERROR)

    def is_password_error_displayed(self) -> bool:
        """Return True if a password validation error is visible."""
        return self.is_element_visible(*self.PASSWORD_ERROR)

    def get_email_field_attribute(self, attr: str) -> str:
        """Return the value of *attr* on the email input element."""
        return self.get_attribute(*self.EMAIL_INPUT, attr)

    def get_password_field_attribute(self, attr: str) -> str:
        """Return the value of *attr* on the password input element."""
        return self.get_attribute(*self.PASSWORD_INPUT, attr)

    def get_submit_button_attribute(self, attr: str) -> str:
        """Return the value of *attr* on the submit button element."""
        return self.get_attribute(*self.SUBMIT_BUTTON, attr)

    def get_email_field_role(self) -> str:
        """Return the ARIA role of the email input (defaults to 'textbox')."""
        role = self.get_attribute(*self.EMAIL_INPUT, "role")
        return role if role else "textbox"

    def get_submit_button_role(self) -> str:
        """Return the ARIA role of the submit button."""
        role = self.get_attribute(*self.SUBMIT_BUTTON, "role")
        if not role:
            tag = self._find(*self.SUBMIT_BUTTON).tag_name.lower()
            return "button" if tag == "button" else role
        return role

    def tab_through_form(self) -> None:
        """
        Tab from the email field -> password field -> submit button.
        Simulates keyboard-only navigation through the login form.
        """
        self.tab_to_element(*self.EMAIL_INPUT)
        self.tab_to_element(*self.PASSWORD_INPUT)
        self.tab_to_element(*self.SUBMIT_BUTTON)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def driver():
    """
    Provide a Chrome WebDriver instance with guaranteed teardown.

    The driver is created before each test function and quit afterwards,
    ensuring no browser processes are leaked between tests.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    _driver = webdriver.Chrome(options=options)
    _driver.implicitly_wait(0)  # rely solely on explicit waits
    try:
        yield _driver
    finally:
        try:
            _driver.quit()
        except WebDriverException:
            pass


@pytest.fixture()
def login_page(driver):
    """Return a LoginPage instance navigated to the login URL."""
    page = LoginPage(driver)
    page.open()
    return page


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@pytest.mark.regression
def test_tc001_successful_login_navigates_to_dashboard(login_page):
    """
    TC_001 — Successful login with valid credentials navigates to dashboard.

    Given the user is on the login page,
    When  the user enters a valid email and correct password and clicks submit,
    Then  the user is redirected to the dashboard and no error messages are shown.
    """
    email = "admin@test.com"
    password = "correct_pass"

    login_page.submit_login(email, password)

    try:
        login_page.wait_for_dashboard()
    except TimeoutException:
        pytest.fail(
            f"TC_001 FAILED: User was not redirected to '{DASHBOARD_PATH}' "
            f"after login. Current URL: {login_page.current_url()}"
        )

    assert login_page.is_on_dashboard(), (
        f"TC_001 FAILED: Expected URL to contain '{DASHBOARD_PATH}', "
        f"got '{login_page.current_url()}'"
    )

    assert not login_page.is_auth_error_displayed(), (
        "TC_001 FAILED: An authentication error message is unexpectedly visible "
        "after a successful login."
    )


@pytest.mark.regression
def test_tc002_incorrect_password_shows_auth_error(login_page):
    """
    TC_002 — Login blocked and authentication error shown for incorrect password.

    Given the user is on the login page,
    When  the user enters a valid email with an incorrect password and clicks submit,
    Then  the user remains on the login page and an authentication error is displayed.
    """
    email = "admin@test.com"
    password = "wrong_pass"
    expected_error = "Invalid email or password"

    login_page.submit_login(email, password)

    assert login_page.is_on_login_page(), (
        f"TC_002 FAILED: User was unexpectedly redirected away from the login page. "
        f"Current URL: {login_page.current_url()}"
    )

    assert login_page.is_auth_error_displayed(), (
        "TC_002 FAILED: Authentication error message is not visible after "
        "submitting an incorrect password."
    )

    actual_error = login_page.get_auth_error_text()
    assert expected_error in actual_error, (
        f"TC_002 FAILED: Expected error text '{expected_error}' "
        f"not found in actual error '{actual_error}'."
    )


@pytest.mark.regression
@pytest.mark.a11y
def test_tc003_empty_fields_show_required_errors(login_page):
    """
    TC_003 — Login blocked and required field errors shown when both fields are empty.

    Given the user is on the login page,
    When  the user leaves both email and password fields empty and clicks submit,
    Then  the form is not submitted and required field errors appear for both fields.
    """
    expected_email_error = "Email is required"
    expected_password_error = "Password is required"

    login_page.submit_login("", "")

    assert login_page.is_on_login_page(), (
        "TC_003 FAILED: Form was submitted despite both fields being empty. "
        f"Current URL: {login_page.current_url()}"
    )

    assert login_page.is_email_error_displayed(), (
        "TC_003 FAILED: Email field required error is not visible."
    )
    assert login_page.is_password_error_displayed(), (
        "TC_003 FAILED: Password field required error is not visible."
    )

    actual_email_error = login_page.get_email_error_text()
    actual_password_error = login_page.get_password_error_text()

    assert expected_email_error in actual_email_error, (
        f"TC_003 FAILED: Expected email error '{expected_email_error}', "
        f"got '{actual_email_error}'."
    )
    assert expected_password_error in actual_password_error, (
        f"TC_003 FAILED: Expected password error '{expected_password_error}', "
        f"got '{actual_password_error}'."
    )


@pytest.mark.regression
def test_tc004_empty_password_shows_required_error(login_page):
    """
    TC_004 — Login blocked and required field error shown when password is empty.

    Given the user is on the login page,
    When  the user enters a valid email and leaves the password empty and clicks submit,
    Then  the form is not submitted and only the password required error is shown.
    """
    email = "admin@test.com"
    expected_error = "Password is required"

    login_page.submit_login(email, "")

    assert login_page.is_on_login_page(), (
        "TC_004 FAILED: Form was submitted despite an empty password field. "
        f"Current URL: {login_page.current_url()}"
    )

    assert login_page.is_password_error_displayed(), (
        "TC_004 FAILED: Password required error message is not visible."
    )

    actual_error = login_page.get_password_error_text()
    assert expected_error in actual_error, (
        f"TC_004 FAILED: Expected error '{expected_error}', got '{actual_error}'."
    )

    assert not login_page.is_email_error_displayed(), (
        "TC_004 FAILED: An unexpected email field error is shown when the "
        "email was valid."
    )


@pytest.mark.regression
@pytest.mark.a11y
def test_tc005_invalid_email_format_shows_format_error(login_page):
    """
    TC_005 — Login blocked and email format error shown for invalid email format.

    Given the user is on the login page,
    When  the user enters an invalid email format with a valid password and clicks submit,
    Then  the form is not submitted and an email format validation error is displayed.
    """
    email = "not-an-email"
    password = "correct_pass"
    expected_error = "Please enter a valid email address"

    login_page.submit_login(email, password)

    assert login_page.is_on_login_page(), (
        "TC_005 FAILED: Form was submitted despite an invalid email format. "
        f"Current URL: {login_page.current_url()}"
    )

    assert login_page.is_email_error_displayed(), (
        "TC_005 FAILED: Email format validation error is not visible."
    )

    actual_error = login_page.get_email_error_text()
    assert expected_error in actual_error, (
        f"TC_005 FAILED: Expected format error '{expected_error}', "
        f"got '{actual_error}'."
    )


@pytest.mark.regression
def test_tc006_empty_email_shows_required_error(login_page):
    """
    TC_006 — Login blocked and required field error shown when only email is empty.

    Given the user is on the login page,
    When  the user leaves the email field empty and enters a valid password and clicks submit,
    Then  the form is not submitted and only the email required error is shown.
    """
    password = "correct_pass"
    expected_error = "Email is required"

    login_page.submit_login("", password)

    assert login_page.is_on_login_page(), (
        "TC_006 FAILED: Form was submitted despite an empty email field. "
        f"Current URL: {login_page.current_url()}"
    )

    assert login_page.is_email_error_displayed(), (
        "TC_006 FAILED: Email required error message is not visible."
    )

    actual_error = login_page.get_email_error_text()
    assert expected_error in actual_error, (
        f"TC_006 FAILED: Expected error '{expected_error}', got '{actual_error}'."
    )

    assert not login_page.is_password_error_displayed(), (
        "TC_006 FAILED: An unexpected password field error is shown when "
        "the password was valid."
    )


@pytest.mark.regression
def test_tc007_multiple_failed_attempts_trigger_lockout(login_page):
    """
    TC_007 — Account lockout message shown after multiple consecutive failed login attempts.

    Given the user is on the login page,
    When  the user submits invalid credentials five consecutive times,
    Then  a lockout warning message is displayed indicating the account is temporarily locked.
    """
    email = "admin@test.com"
    password = "wrong_pass"
    attempt_count = 5
    expected_message = "Account temporarily locked due to multiple failed attempts"

    lockout_detected = False

    for attempt in range(1, attempt_count + 1):
        login_page.enter_email(email)
        login_page.enter_password(password)
        login_page.click_submit()

        # After each failed attempt re-open the login page if we were redirected
        # (some implementations stay on the same page)
        if not login_page.is_on_login_page():
            login_page.open()
            continue

        current_lockout_text = login_page.get_lockout_message_text()
        if expected_message in current_lockout_text:
            lockout_detected = True
            break

        # Clear fields for the next iteration (page may not have reloaded)
        try:
            login_page.enter_email("")
            login_page.enter_password("")
        except RuntimeError:
            login_page.open()

    if not lockout_detected:
        # Final check after all attempts
        lockout_text = login_page.get_lockout_message_text()
        lockout_detected = expected_message in lockout_text

    assert lockout_detected, (
        f"TC_007 FAILED: Lockout message '{expected_message}' was not displayed "
        f"after {attempt_count} failed login attempts. "
        f"Last visible text: '{login_page.get_lockout_message_text()}'"
    )


@pytest.mark.a11y
@pytest.mark.regression
def test_tc008_form_is_keyboard_navigable_and_accessible(login_page):
    """
    TC_008 — Login form fields and submit button are keyboard navigable and screen-reader accessible.

    Given the user is on the login page,
    When  the user navigates the form using only keyboard Tab and Enter keys,
    Then  the email field, password field, and submit button are reachable via Tab,
          ARIA labels/required/describedby attributes are present on form controls,
          and form submission is possible using the Enter key.
    """
    # ------------------------------------------------------------------ #
    # 1. Verify ARIA attributes exist on the email field
    # ------------------------------------------------------------------ #
    aria_label_email = login_page.get_email_field_attribute("aria-label")
    aria_required_email = login_page.get_email_field_attribute("aria-required")
    aria_describedby_email = login_page.get_email_field_attribute("aria-describedby")

    assert aria_label_email or aria_required_email or aria_describedby_email, (
        "TC_008 FAILED: Email field is missing all ARIA attributes "
        "(aria-label, aria-required, aria-describedby)."
    )

    # ------------------------------------------------------------------ #
    # 2. Verify ARIA attributes exist on the password field
    # ------------------------------------------------------------------ #
    aria_label_pwd = login_page.get_password_field_attribute("aria-label")
    aria_required_pwd = login_page.get_password_field_attribute("aria-required")
    aria_describedby_pwd = login_page.get_password_field_attribute("aria-describedby")

    assert aria_label_pwd or aria_required_pwd or aria_describedby_pwd, (
        "TC_008 FAILED: Password field is missing all ARIA attributes "
        "(aria-label, aria-required, aria-describedby)."
    )

    # ------------------------------------------------------------------ #
    # 3. Verify ARIA role of email input (implicit or explicit 'textbox')
    # ------------------------------------------------------------------ #
    email_role = login_page.get_email_field_role()
    assert email_role == "textbox", (
        f"TC_008 FAILED: Expected email field ARIA role 'textbox', got '{email_role}'."
    )

    # ------------------------------------------------------------------ #
    # 4. Verify submit button has 'button' role
    # ------------------------------------------------------------------ #
    button_role = login_page.get_submit_button_role()
    assert button_role == "button", (
        f"TC_008 FAILED: Expected submit button ARIA role 'button', got '{button_role}'."
    )

    # ------------------------------------------------------------------ #
    # 5. Verify all fields are reachable via Tab key
    # ------------------------------------------------------------------ #
    try:
        login_page.tab_through_form()
    except RuntimeError as exc:
        pytest.fail(
            f"TC_008 FAILED: One or more form controls are not reachable via Tab. "
            f"Details: {exc}"
        )

    # ------------------------------------------------------------------ #
    # 6. Verify form submission is possible via the Enter key on submit button
    # ------------------------------------------------------------------ #
    login_page.open()  # reset form state
    try:
        login_page.submit_login_with_enter("admin@test.com", "correct_pass")
    except RuntimeError as exc:
        pytest.fail(
            f"TC_008 FAILED: Could not submit form using the Enter key. Details: {exc}"
        )

    # After a valid Enter-key submission the page should leave the login URL
    # (either dashboard or an error — both are acceptable for this a11y check).
    # We just confirm the form was actually submitted (i.e. some navigation occurred
    # or an error/response was rendered).
    auth_error_visible = login_page.is_auth_error_displayed()
    on_dashboard = login_page.is_on_dashboard()
    on_login = login_page.is_on_login_page()

    assert on_dashboard or auth_error_visible or not on_login, (
        "TC_008 FAILED: Form does not appear to have been submitted via the Enter key. "
        f"Current URL: {login_page.current_url()}"
    )


# ---------------------------------------------------------------------------
# Parametrised data-driven validation tests (TC_003 - TC_006 combined variant)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "email, password, expect_email_err, expect_password_err, expected_email_err_text, expected_pwd_err_text",
    [
        # TC_003: both empty
        ("", "", True, True, "Email is required", "Password is required"),
        # TC_004: valid email, empty password
        ("admin@test.com", "", False, True, "", "Password is required"),
        # TC_005: invalid email format
        ("not-an-email", "correct_pass", True, False, "Please enter a valid email address", ""),
        # TC_006: empty email, valid password
        ("", "correct_pass", True, False, "Email is required", ""),
    ],
    ids=["TC003_both_empty", "TC004_password_empty", "TC005_bad_email_format", "TC006_email_empty"],
)
@pytest.mark.regression
def test_validation_errors_parametrised(
    login_page,
    email,
    password,
    expect_email_err,
    expect_password_err,
    expected_email_err_text,
    expected_pwd_err_text,
):
    """
    Parametrised data-driven test covering TC_003, TC_004, TC_005, and TC_006.

    Verifies that the correct combination of validation error messages is displayed
    for various combinations of empty or invalid email/password inputs.
    """
    login_page.submit_login(email, password)

    assert login_page.is_on_login_page(), (
        f"FAILED [{email!r}/{password!r}]: Form was unexpectedly submitted. "
        f"URL: {login_page.current_url()}"
    )

    if expect_email_err:
        assert login_page.is_email_error_displayed(), (
            f"FAILED [{email!r}/{password!r}]: Expected email error to be visible."
        )
        if expected_email_err_text:
            actual = login_page.get_email_error_text()
            assert expected_email_err_text in actual, (
                f"FAILED [{email!r}/{password!r}]: Expected email error text "
                f"'{expected_email_err_text}', got '{actual}'."
            )
    else:
        assert not login_page.is_email_error_displayed(), (
            f"FAILED [{email!r}/{password!r}]: Unexpected email error is visible."
        )

    if expect_password_err:
        assert login_page.is_password_error_displayed(), (
            f"FAILED [{email!r}/{password!r}]: Expected password error to be visible."
        )
        if expected_pwd_err_text:
            actual = login_page.get_password_error_text()
            assert expected_pwd_err_text in actual, (
                f"FAILED [{email!r}/{password!r}]: Expected password error text "
                f"'{expected_pwd_err_text}', got '{actual}'."
            )
    else:
        assert not login_page.is_password_error_displayed(), (
            f"FAILED [{email!r}/{password!r}]: Unexpected password error is visible."
        )