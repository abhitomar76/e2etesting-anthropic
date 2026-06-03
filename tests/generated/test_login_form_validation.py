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
# Configuration constants — read from environment variables, never hard-coded
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "http://localhost")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))


# ---------------------------------------------------------------------------
# Base Page
# ---------------------------------------------------------------------------

class BasePage:
    """Provides shared driver utilities for all page objects."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def navigate(self, path: str = "") -> None:
        """Navigate to BASE_URL + path."""
        try:
            self.driver.get(f"{BASE_URL}{path}")
        except WebDriverException as exc:
            raise RuntimeError(f"Navigation to '{path}' failed: {exc}") from exc

    def find(self, by: str, value: str):
        """Wait for element visibility and return it."""
        try:
            return self.wait.until(
                EC.visibility_of_element_located((by, value)),
                message=f"Element ({by}='{value}') not visible within {DEFAULT_TIMEOUT}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Element ({by}='{value}') not visible within {DEFAULT_TIMEOUT}s"
            ) from exc

    def find_clickable(self, by: str, value: str):
        """Wait for element to be clickable and return it."""
        try:
            return self.wait.until(
                EC.element_to_be_clickable((by, value)),
                message=f"Element ({by}='{value}') not clickable within {DEFAULT_TIMEOUT}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Element ({by}='{value}') not clickable within {DEFAULT_TIMEOUT}s"
            ) from exc

    def type_text(self, by: str, value: str, text: str) -> None:
        """Clear the field and type text (no-op for empty string)."""
        try:
            element = self.find(by, value)
            element.clear()
            if text:
                element.send_keys(text)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not type into ({by}='{value}'): {exc}"
            ) from exc

    def click(self, by: str, value: str) -> None:
        """Click a web element after waiting for it to be clickable."""
        try:
            self.find_clickable(by, value).click()
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(f"Could not click ({by}='{value}'): {exc}") from exc

    def wait_for_url_contains(self, fragment: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Block until the current URL contains *fragment*."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(fragment),
                message=f"URL did not contain '{fragment}' within {timeout}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"URL did not contain '{fragment}' within {timeout}s. "
                f"Current URL: {self.driver.current_url}"
            ) from exc

    def is_element_present(self, by: str, value: str, timeout: int = 5) -> bool:
        """Return True if element becomes visible within *timeout* seconds."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def get_element_attribute(self, by: str, value: str, attribute: str) -> str:
        """Return the value of *attribute* for the located element."""
        try:
            element = self.find(by, value)
            return element.get_attribute(attribute) or ""
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not read attribute '{attribute}' from ({by}='{value}'): {exc}"
            ) from exc

    def get_element_text(self, by: str, value: str) -> str:
        """Return visible text of the located element."""
        try:
            return self.find(by, value).text
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not read text from ({by}='{value}'): {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Login Page Object
# ---------------------------------------------------------------------------

class LoginPage(BasePage):
    """Page object for the login form at /login."""

    # -- Locators (priority: data-testid > ARIA > CSS > XPath) --------------
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"]')

    # Error containers
    EMAIL_ERROR = (By.CSS_SELECTOR, '[data-testid="email-error"]')
    PASSWORD_ERROR = (By.CSS_SELECTOR, '[data-testid="password-error"]')
    AUTH_ERROR = (By.CSS_SELECTOR, '[data-testid="auth-error"]')

    # Dashboard landmark (post-login)
    DASHBOARD_HEADING = (By.CSS_SELECTOR, '[data-testid="dashboard-heading"]')

    # Fallback ARIA-based locators used in accessibility test.
    # Fixed: use stable @for attribute only — avoids i18n breakage from contains(text())
    _EMAIL_LABEL = (By.CSS_SELECTOR, 'label[for="email"]')
    _PASSWORD_LABEL = (By.CSS_SELECTOR, 'label[for="password"]')
    # Fixed: replaced brittle translate() XPath with a stable CSS aria-label selector
    _SUBMIT_ARIA = (By.CSS_SELECTOR, 'button[type="submit"][aria-label], button[data-testid="login-submit"]')

    def open(self) -> "LoginPage":
        """Navigate to the login page and return self for chaining."""
        self.navigate("/login")
        # Ensure the email field is present before proceeding
        self.find(*self.EMAIL_INPUT)
        return self

    def enter_email(self, email: str) -> "LoginPage":
        """Enter *email* into the email field."""
        self.type_text(*self.EMAIL_INPUT, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Enter *password* into the password field."""
        self.type_text(*self.PASSWORD_INPUT, password)
        return self

    def click_submit(self) -> "LoginPage":
        """Click the submit / login button."""
        self.click(*self.SUBMIT_BUTTON)
        return self

    def submit_with_keyboard(self) -> "LoginPage":
        """Press Enter on the submit button to activate it via keyboard."""
        try:
            btn = self.find_clickable(*self.SUBMIT_BUTTON)
            btn.send_keys(Keys.RETURN)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(f"Keyboard submit failed: {exc}") from exc
        return self

    def login(self, email: str, password: str) -> None:
        """High-level helper: open page, fill form, click submit."""
        self.open()
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()

    # -- Assertion helpers ---------------------------------------------------

    def is_on_dashboard(self) -> bool:
        """Return True when the browser has landed on the dashboard."""
        try:
            self.wait_for_url_contains("/dashboard")
            return True
        except TimeoutException:
            return False

    def is_on_login_page(self) -> bool:
        """Return True when the URL still contains '/login'."""
        return "/login" in self.driver.current_url

    def auth_error_is_displayed(self) -> bool:
        """Return True when a generic authentication error banner is visible."""
        return self.is_element_present(*self.AUTH_ERROR)

    def email_error_is_displayed(self) -> bool:
        """Return True when the email field validation error is visible."""
        return self.is_element_present(*self.EMAIL_ERROR)

    def password_error_is_displayed(self) -> bool:
        """Return True when the password field validation error is visible."""
        return self.is_element_present(*self.PASSWORD_ERROR)

    def no_error_messages_displayed(self) -> bool:
        """Return True when no error elements are visible on the page."""
        return (
            not self.is_element_present(*self.AUTH_ERROR, timeout=2)
            and not self.is_element_present(*self.EMAIL_ERROR, timeout=2)
            and not self.is_element_present(*self.PASSWORD_ERROR, timeout=2)
        )

    def get_email_input_aria_label(self) -> str:
        """Return the aria-label attribute of the email input."""
        return self.get_element_attribute(*self.EMAIL_INPUT, "aria-label")

    def get_password_input_aria_label(self) -> str:
        """Return the aria-label attribute of the password input."""
        return self.get_element_attribute(*self.PASSWORD_INPUT, "aria-label")

    def get_email_input_role(self) -> str:
        """Return the role attribute of the email input (implicit 'textbox')."""
        return self.get_element_attribute(*self.EMAIL_INPUT, "role") or "textbox"

    def get_password_input_type(self) -> str:
        """Return the type attribute of the password input."""
        return self.get_element_attribute(*self.PASSWORD_INPUT, "type")

    def tab_through_form(self) -> None:
        """
        Drive focus through the form with Tab: email → password → submit.
        Raises RuntimeError if focus order is incorrect.
        """
        try:
            email_el = self.find(*self.EMAIL_INPUT)
            email_el.click()  # set initial focus
            # Tab to password
            email_el.send_keys(Keys.TAB)
            active = self.driver.switch_to.active_element
            password_el = self.find(*self.PASSWORD_INPUT)
            if active.id != password_el.id:
                raise RuntimeError(
                    "Tab from email did not move focus to the password field. "
                    f"Active element id={active.id}, password id={password_el.id}"
                )
            # Tab to submit
            active.send_keys(Keys.TAB)
            active2 = self.driver.switch_to.active_element
            submit_el = self.find(*self.SUBMIT_BUTTON)
            if active2.id != submit_el.id:
                raise RuntimeError(
                    "Tab from password did not move focus to the submit button. "
                    f"Active element id={active2.id}, submit id={submit_el.id}"
                )
        except WebDriverException as exc:
            raise RuntimeError(f"Keyboard navigation through form failed: {exc}") from exc

    def error_has_aria_live(self) -> bool:
        """
        Return True when at least one error container carries an aria-live
        attribute (required for screen-reader announcements).
        """
        for locator in (self.EMAIL_ERROR, self.PASSWORD_ERROR, self.AUTH_ERROR):
            if self.is_element_present(*locator, timeout=2):
                try:
                    el = self.find(*locator)
                    live = el.get_attribute("aria-live") or ""
                    if live in ("polite", "assertive"):
                        return True
                except (TimeoutException, NoSuchElementException):
                    pass
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def driver():
    """
    Session-scoped WebDriver fixture.
    Yields the driver instance and guarantees quit() in a finally block
    so the browser is always closed regardless of test outcome.
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
        _driver.quit()


@pytest.fixture
def login_page(driver):
    """Return a LoginPage instance bound to the shared driver fixture."""
    return LoginPage(driver)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@pytest.mark.regression
def test_TC_001_successful_login_navigates_to_dashboard(login_page):
    """
    TC_001 – Verifies that a user with valid credentials is redirected to the
    dashboard after submitting the login form, and that no error messages are
    present on the resulting page.
    """
    email = "admin@test.com"
    password = "correct_pass"

    login_page.login(email, password)

    assert login_page.is_on_dashboard(), (
        f"Expected redirect to /dashboard after valid login, "
        f"but current URL is: {login_page.driver.current_url}"
    )
    assert login_page.no_error_messages_displayed(), (
        "No error messages should be visible after a successful login."
    )


@pytest.mark.regression
def test_TC_002_incorrect_password_shows_auth_error(login_page):
    """
    TC_002 – Verifies that submitting the login form with a correct email but
    wrong password keeps the user on the login page and displays an
    authentication error message.
    """
    email = "admin@test.com"
    password = "wrong_pass"

    login_page.login(email, password)

    assert login_page.is_on_login_page(), (
        "User should remain on the login page after an incorrect-password attempt."
    )
    assert login_page.auth_error_is_displayed(), (
        "An authentication error message must be displayed for an incorrect password."
    )


@pytest.mark.regression
def test_TC_003_empty_fields_show_required_errors(login_page):
    """
    TC_003 – Verifies that submitting the login form with both email and
    password fields empty prevents form submission and displays required-field
    validation errors for both fields.
    """
    login_page.open()
    login_page.click_submit()

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when both fields are empty."
    )
    assert login_page.email_error_is_displayed(), (
        "A required-field error must be shown for the email field when it is empty."
    )
    assert login_page.password_error_is_displayed(), (
        "A required-field error must be shown for the password field when it is empty."
    )


@pytest.mark.regression
def test_TC_004_empty_password_shows_password_required_error(login_page):
    """
    TC_004 – Verifies that submitting the login form with a valid email but an
    empty password field prevents form submission and shows a required-field
    error only for the password field.
    """
    login_page.open()
    login_page.enter_email("admin@test.com")
    login_page.click_submit()

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when the password field is empty."
    )
    assert login_page.password_error_is_displayed(), (
        "A required-field error must be shown for the password field."
    )
    assert not login_page.email_error_is_displayed(), (
        "No email error should be shown when a valid email has been entered."
    )


@pytest.mark.regression
def test_TC_005_empty_email_shows_email_required_error(login_page):
    """
    TC_005 – Verifies that submitting the login form with the email field empty
    (but a valid password provided) prevents form submission and shows a
    required-field error only for the email field.
    """
    login_page.open()
    login_page.enter_password("correct_pass")
    login_page.click_submit()

    assert login_page.is_on_login_page(), (
        "Form should not be submitted when the email field is empty."
    )
    assert login_page.email_error_is_displayed(), (
        "A required-field error must be shown for the email field."
    )
    assert not login_page.password_error_is_displayed(), (
        "No password error should be shown when a valid password has been entered."
    )


@pytest.mark.regression
@pytest.mark.parametrize(
    "invalid_email",
    [
        "not-an-email",
        "missing@",
        "@nodomain.com",
        "spaces in@email.com",
        "plainaddress",
    ],
)
def test_TC_006_invalid_email_format_shows_format_error(login_page, invalid_email):
    """
    TC_006 – Verifies that submitting the login form with a malformed email
    address (parametrised across several invalid formats) and a valid password
    prevents form submission and displays an email format validation error.
    """
    login_page.open()
    login_page.enter_email(invalid_email)
    login_page.enter_password("correct_pass")
    login_page.click_submit()

    assert login_page.is_on_login_page(), (
        f"Form should not be submitted for invalid email '{invalid_email}'."
    )
    assert login_page.email_error_is_displayed(), (
        f"An email format validation error must be shown for '{invalid_email}'."
    )


@pytest.mark.regression
def test_TC_007_nonexistent_user_shows_generic_auth_error(login_page):
    """
    TC_007 – Verifies that submitting the login form with an email address that
    does not exist in the system keeps the user on the login page and shows a
    generic authentication error (without revealing whether the email exists,
    to prevent user enumeration).
    """
    email = "nonexistent@test.com"
    password = "any_pass"

    login_page.login(email, password)

    assert login_page.is_on_login_page(), (
        "User should remain on the login page when the account does not exist."
    )
    assert login_page.auth_error_is_displayed(), (
        "A generic authentication error must be displayed for a non-existent account."
    )
    # The error text must NOT reveal that the email specifically doesn't exist.
    try:
        error_text = login_page.get_element_text(*LoginPage.AUTH_ERROR).lower()
    except RuntimeError:
        error_text = ""

    enumeration_hints = ["email not found", "no account", "user not found", "does not exist"]
    for hint in enumeration_hints:
        assert hint not in error_text, (
            f"Error message must not reveal user-enumeration information. "
            f"Found hint '{hint}' in: '{error_text}'"
        )


@pytest.mark.a11y
@pytest.mark.regression
def test_TC_008_login_form_keyboard_and_aria_accessibility(login_page):
    """
    TC_008 – Verifies that the login form is fully accessible:
      * Email and password inputs carry accessible labels / aria-label attributes.
      * The password input has type='password'.
      * Focus order follows the expected sequence email → password → submit when
        navigating with the Tab key.
      * After triggering a validation error via keyboard-activated submit, the
        error containers carry an aria-live attribute so assistive technology
        can announce them.
    """
    login_page.open()

    # 1. Accessible labels are present on the inputs
    email_label = login_page.get_email_input_aria_label()
    assert email_label, (
        "The email input must have a non-empty aria-label for screen-reader accessibility."
    )

    password_label = login_page.get_password_input_aria_label()
    assert password_label, (
        "The password input must have a non-empty aria-label for screen-reader accessibility."
    )

    # 2. Password field type must be 'password' (masks input)
    password_type = login_page.get_password_input_type()
    assert password_type == "password", (
        f"Password input type should be 'password', got '{password_type}'."
    )

    # 3. Tab order: email → password → submit
    login_page.tab_through_form()

    # 4. Submit via keyboard (Enter on focused submit button), then check aria-live
    login_page.submit_with_keyboard()

    # Errors should appear because no credentials were entered
    assert login_page.email_error_is_displayed() or login_page.password_error_is_displayed(), (
        "Validation errors should be displayed after submitting an empty form."
    )

    assert login_page.error_has_aria_live(), (
        "At least one error container must have aria-live='polite' or 'assertive' "
        "so that assistive technology announces the validation failure."
    )