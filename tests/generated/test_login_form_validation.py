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
# Configuration constants — loaded from environment variables with safe defaults
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "http://localhost")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))
LOGIN_PATH = os.getenv("LOGIN_PATH", "/login")
DASHBOARD_PATH = os.getenv("DASHBOARD_PATH", "/dashboard")

# ---------------------------------------------------------------------------
# Base Page
# ---------------------------------------------------------------------------

class BasePage:
    """Shared driver wrapper used by all page objects."""

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
        """Wait for an element to be present and return it."""
        try:
            return self.wait.until(
                EC.presence_of_element_located((by, value)),
                message=f"Element not found: ({by}, {value})",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for element ({by}, '{value}')"
            ) from exc

    def find_visible(self, by: str, value: str):
        """Wait for an element to be visible and return it."""
        try:
            return self.wait.until(
                EC.visibility_of_element_located((by, value)),
                message=f"Element not visible: ({by}, {value})",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for visible element ({by}, '{value}')"
            ) from exc

    def find_clickable(self, by: str, value: str):
        """Wait for an element to be clickable and return it."""
        try:
            return self.wait.until(
                EC.element_to_be_clickable((by, value)),
                message=f"Element not clickable: ({by}, {value})",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for clickable element ({by}, '{value}')"
            ) from exc

    def type_text(self, by: str, value: str, text: str) -> None:
        """Clear a field and type the given text into it."""
        try:
            element = self.find_visible(by, value)
            element.clear()
            if text:
                element.send_keys(text)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to type text into ({by}, '{value}'): {exc}"
            ) from exc

    def click(self, by: str, value: str) -> None:
        """Click a clickable element."""
        try:
            self.find_clickable(by, value).click()
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to click element ({by}, '{value}'): {exc}"
            ) from exc

    def wait_for_url_contains(self, fragment: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Block until the current URL contains the given fragment."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(fragment),
                message=f"URL did not contain '{fragment}' within {timeout}s",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"URL '{self.driver.current_url}' did not contain '{fragment}' "
                f"within {timeout}s"
            ) from exc

    def is_element_present(self, by: str, value: str, timeout: int = 5) -> bool:
        """Return True if the element appears within *timeout* seconds."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def get_current_url(self) -> str:
        """Return the current browser URL."""
        try:
            return self.driver.current_url
        except WebDriverException as exc:
            raise RuntimeError(f"Unable to retrieve current URL: {exc}") from exc

    def get_element_attribute(self, by: str, value: str, attribute: str) -> str:
        """Return the value of an element attribute."""
        try:
            return self.find(by, value).get_attribute(attribute) or ""
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to get attribute '{attribute}' from ({by}, '{value}'): {exc}"
            ) from exc

    def send_tab_to(self, by: str, value: str) -> None:
        """Send a TAB keystroke to the specified element."""
        try:
            self.find_visible(by, value).send_keys(Keys.TAB)
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(
                f"Failed to send TAB to ({by}, '{value}'): {exc}"
            ) from exc

    def get_active_element(self):
        """Return the currently focused element."""
        try:
            return self.driver.switch_to.active_element
        except WebDriverException as exc:
            raise RuntimeError(f"Unable to get active element: {exc}") from exc


# ---------------------------------------------------------------------------
# Login Page Object
# ---------------------------------------------------------------------------

class LoginPage(BasePage):
    """Page object encapsulating all interactions with the login form."""

    # -- Locators (preference: data-testid > ARIA > CSS > XPath) ------------
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"], [name="email"], #email')
    PASSWORD_INPUT = (
        By.CSS_SELECTOR,
        '[data-testid="password"], [name="password"], #password',
    )
    # Fixed: replaced brittle compound absolute XPath with a single data-testid CSS selector
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"]')

    # Error / validation message selectors
    AUTH_ERROR = (
        By.CSS_SELECTOR,
        '[data-testid="auth-error"], [role="alert"], .error-message, .alert-danger',
    )
    EMAIL_ERROR = (
        By.CSS_SELECTOR,
        '[data-testid="email-error"], #email-error, [for="email"] ~ .error, '
        '[aria-describedby*="email"] + .error',
    )
    PASSWORD_ERROR = (
        By.CSS_SELECTOR,
        '[data-testid="password-error"], #password-error, [for="password"] ~ .error, '
        '[aria-describedby*="password"] + .error',
    )

    # -- Navigation ----------------------------------------------------------

    def open(self) -> "LoginPage":
        """Load the login page."""
        self.navigate(LOGIN_PATH)
        # Confirm the email field is rendered before proceeding
        self.find_visible(*self.EMAIL_INPUT)
        return self

    # -- Actions -------------------------------------------------------------

    def enter_email(self, email: str) -> "LoginPage":
        """Type *email* into the email field (empty string clears the field)."""
        self.type_text(*self.EMAIL_INPUT, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Type *password* into the password field."""
        self.type_text(*self.PASSWORD_INPUT, password)
        return self

    def click_submit(self) -> "LoginPage":
        """Click the submit / login button."""
        self.click(*self.SUBMIT_BUTTON)
        return self

    def login(self, email: str, password: str) -> "LoginPage":
        """Full login flow: enter credentials and submit."""
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()
        return self

    # -- Assertions / state queries -----------------------------------------

    def is_on_login_page(self) -> bool:
        """Return True if the current URL still points to the login path."""
        return LOGIN_PATH in self.get_current_url()

    def is_on_dashboard(self) -> bool:
        """Return True if redirected to the dashboard path."""
        return DASHBOARD_PATH in self.get_current_url()

    def wait_for_dashboard(self) -> None:
        """Block until the dashboard URL fragment is present."""
        self.wait_for_url_contains(DASHBOARD_PATH)

    def has_auth_error(self) -> bool:
        """Return True if a generic authentication error is visible."""
        return self.is_element_present(*self.AUTH_ERROR)

    def has_email_error(self) -> bool:
        """Return True if an email-specific validation error is visible."""
        return self.is_element_present(*self.EMAIL_ERROR)

    def has_password_error(self) -> bool:
        """Return True if a password-specific validation error is visible."""
        return self.is_element_present(*self.PASSWORD_ERROR)

    def get_auth_error_text(self) -> str:
        """Return the visible authentication error message text."""
        try:
            element = self.find_visible(*self.AUTH_ERROR)
            return element.text.strip()
        except TimeoutException:
            return ""

    def get_email_field_aria_label(self) -> str:
        """Return the aria-label attribute of the email input."""
        return self.get_element_attribute(*self.EMAIL_INPUT, "aria-label")

    def get_password_field_aria_label(self) -> str:
        """Return the aria-label attribute of the password input."""
        return self.get_element_attribute(*self.PASSWORD_INPUT, "aria-label")

    def get_submit_button_role(self) -> str:
        """Return the role attribute (or tag-derived role) of the submit button."""
        try:
            element = self.find(*self.SUBMIT_BUTTON)
            role = element.get_attribute("role") or element.tag_name
            return role
        except (TimeoutException, WebDriverException) as exc:
            raise RuntimeError(f"Unable to inspect submit button role: {exc}") from exc

    def tab_through_form(self) -> list:
        """
        Tab through the login form starting from the email field.
        Returns a list of (tag_name, id_or_name) tuples representing focus order.
        """
        focus_order = []
        try:
            # Focus the email field first
            email_el = self.find_visible(*self.EMAIL_INPUT)
            email_el.click()
            focus_order.append(
                (email_el.tag_name, email_el.get_attribute("name") or email_el.get_attribute("id"))
            )
            # Tab to password
            email_el.send_keys(Keys.TAB)
            active = self.get_active_element()
            focus_order.append(
                (active.tag_name, active.get_attribute("name") or active.get_attribute("id"))
            )
            # Tab to submit
            active.send_keys(Keys.TAB)
            active = self.get_active_element()
            focus_order.append(
                (active.tag_name, active.get_attribute("type") or active.get_attribute("id"))
            )
        except WebDriverException as exc:
            raise RuntimeError(f"Error during keyboard tab traversal: {exc}") from exc
        return focus_order


# ---------------------------------------------------------------------------
# Dashboard Page Object (minimal — used only to verify successful login)
# ---------------------------------------------------------------------------

class DashboardPage(BasePage):
    """Minimal page object for the post-login dashboard."""

    DASHBOARD_INDICATOR = (
        By.CSS_SELECTOR,
        '[data-testid="dashboard"], #dashboard, .dashboard, main',
    )

    def is_loaded(self) -> bool:
        """Return True when a recognisable dashboard element is present."""
        return self.is_element_present(*self.DASHBOARD_INDICATOR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def driver():
    """
    Provide a configured Chrome WebDriver instance.
    Ensures driver.quit() is called after every test via yield + finally teardown.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    _driver = webdriver.Chrome(options=options)
    _driver.implicitly_wait(0)
    try:
        yield _driver
    finally:
        _driver.quit()


@pytest.fixture
def login_page(driver):
    """Provide an opened LoginPage instance; driver fixture supplies the browser."""
    page = LoginPage(driver)
    page.open()
    return page


@pytest.fixture
def dashboard_page(driver):
    """Provide a DashboardPage instance bound to the shared driver."""
    return DashboardPage(driver)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTC001SuccessfulLogin:
    """TC_001 — Successful login with valid credentials navigates to dashboard."""

    @pytest.mark.smoke
    @pytest.mark.regression
    def test_valid_credentials_redirect_to_dashboard(self, login_page, dashboard_page):
        """
        Verifies that submitting correct email and password redirects
        the user to the dashboard URL and that no error messages are
        present after the redirect.
        """
        try:
            login_page.login(email="admin@test.com", password="correct_pass")
            login_page.wait_for_dashboard()
        except TimeoutException as exc:
            pytest.fail(
                f"TC_001: User was not redirected to the dashboard after valid login. "
                f"Current URL: {login_page.get_current_url()}. Error: {exc}"
            )

        assert login_page.is_on_dashboard(), (
            f"TC_001: Expected dashboard URL but got '{login_page.get_current_url()}'"
        )
        assert not login_page.has_auth_error(), (
            "TC_001: An authentication error message was unexpectedly displayed "
            "after successful login."
        )
        assert dashboard_page.is_loaded(), (
            "TC_001: Dashboard page element not found after redirect."
        )


class TestTC002IncorrectPassword:
    """TC_002 — Login blocked and authentication error shown for incorrect password."""

    @pytest.mark.regression
    def test_wrong_password_shows_auth_error(self, login_page):
        """
        Verifies that submitting a correct email with an incorrect password
        keeps the user on the login page and displays an authentication error.
        """
        try:
            login_page.login(email="admin@test.com", password="wrong_pass")
        except RuntimeError as exc:
            pytest.fail(f"TC_002: Unexpected error during login attempt: {exc}")

        assert login_page.is_on_login_page(), (
            f"TC_002: User should remain on login page but URL is "
            f"'{login_page.get_current_url()}'"
        )
        assert login_page.has_auth_error(), (
            "TC_002: Expected an authentication error message but none was found."
        )
        error_text = login_page.get_auth_error_text()
        assert error_text, (
            "TC_002: Authentication error element is present but contains no text."
        )


class TestTC003BothFieldsEmpty:
    """TC_003 — Login blocked and required field errors shown when both fields are empty."""

    @pytest.mark.regression
    def test_empty_fields_show_validation_errors(self, login_page):
        """
        Verifies that submitting the login form with both email and password
        empty prevents submission and shows required-field validation errors
        for both inputs.
        """
        try:
            login_page.login(email="", password="")
        except RuntimeError as exc:
            pytest.fail(f"TC_003: Unexpected error during empty form submission: {exc}")

        assert login_page.is_on_login_page(), (
            f"TC_003: Form should not have been submitted; URL is "
            f"'{login_page.get_current_url()}'"
        )
        assert login_page.has_email_error(), (
            "TC_003: Expected a required-field error for the email field but none appeared."
        )
        assert login_page.has_password_error(), (
            "TC_003: Expected a required-field error for the password field but none appeared."
        )


class TestTC004EmptyPassword:
    """TC_004 — Login blocked and required field error shown when password field is empty."""

    @pytest.mark.regression
    def test_empty_password_shows_password_error_only(self, login_page):
        """
        Verifies that submitting with a valid email but empty password
        prevents form submission and shows a required-field error only
        for the password field, not the email field.
        """
        try:
            login_page.login(email="admin@test.com", password="")
        except RuntimeError as exc:
            pytest.fail(f"TC_004: Unexpected error during partial form submission: {exc}")

        assert login_page.is_on_login_page(), (
            f"TC_004: Form should not have been submitted; URL is "
            f"'{login_page.get_current_url()}'"
        )
        assert login_page.has_password_error(), (
            "TC_004: Expected a required-field error for the password field but none appeared."
        )
        assert not login_page.has_email_error(), (
            "TC_004: Did not expect an email error when a valid email was provided."
        )


class TestTC005EmptyEmail:
    """TC_005 — Login blocked and email validation error shown when email field is empty."""

    @pytest.mark.regression
    def test_empty_email_shows_email_error_only(self, login_page):
        """
        Verifies that submitting with an empty email but valid password
        prevents form submission and shows a required-field error only
        for the email field, not the password field.
        """
        try:
            login_page.login(email="", password="correct_pass")
        except RuntimeError as exc:
            pytest.fail(f"TC_005: Unexpected error during partial form submission: {exc}")

        assert login_page.is_on_login_page(), (
            f"TC_005: Form should not have been submitted; URL is "
            f"'{login_page.get_current_url()}'"
        )
        assert login_page.has_email_error(), (
            "TC_005: Expected a required-field error for the email field but none appeared."
        )
        assert not login_page.has_password_error(), (
            "TC_005: Did not expect a password error when a valid password was provided."
        )


class TestTC006InvalidEmailFormat:
    """TC_006 — Login blocked and format error shown when email format is invalid."""

    @pytest.mark.regression
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
        Verifies that submitting a malformed email address with a valid password
        prevents form submission and shows an email format validation error.
        Parameterised across several invalid email patterns.
        """
        try:
            login_page.login(email=malformed_email, password="correct_pass")
        except RuntimeError as exc:
            pytest.fail(
                f"TC_006: Unexpected error submitting malformed email "
                f"'{malformed_email}': {exc}"
            )

        assert login_page.is_on_login_page(), (
            f"TC_006: Form should not have been submitted for email '{malformed_email}'; "
            f"URL is '{login_page.get_current_url()}'"
        )
        assert login_page.has_email_error(), (
            f"TC_006: Expected an email format validation error for '{malformed_email}' "
            f"but none was displayed."
        )


class TestTC007NonExistentUser:
    """TC_007 — Login blocked and error shown for non-existent user account."""

    @pytest.mark.regression
    def test_nonexistent_user_shows_generic_auth_error(self, login_page):
        """
        Verifies that submitting credentials for an email that does not exist
        in the system keeps the user on the login page and shows a generic
        authentication error message — without revealing whether the account
        exists (no 'user not found' wording should be used).
        """
        try:
            login_page.login(email="nonexistent@test.com", password="any_pass")
        except RuntimeError as exc:
            pytest.fail(f"TC_007: Unexpected error during login attempt: {exc}")

        assert login_page.is_on_login_page(), (
            f"TC_007: User should remain on login page but URL is "
            f"'{login_page.get_current_url()}'"
        )
        assert login_page.has_auth_error(), (
            "TC_007: Expected a generic authentication error but none was displayed."
        )

        # Security check: error must not reveal account existence
        error_text = login_page.get_auth_error_text().lower()
        account_disclosure_phrases = [
            "user not found",
            "account does not exist",
            "no account",
            "email not registered",
        ]
        for phrase in account_disclosure_phrases:
            assert phrase not in error_text, (
                f"TC_007: Error message discloses account existence with phrase '{phrase}'. "
                f"Full message: '{error_text}'"
            )


class TestTC008AccessibilityAndKeyboardNavigation:
    """TC_008 — Login form fields and submit button are accessible via ARIA and keyboard."""

    @pytest.mark.a11y
    @pytest.mark.regression
    def test_form_elements_have_aria_attributes(self, login_page):
        """
        Verifies that the email field, password field, and submit button each
        carry appropriate ARIA labels or roles so that assistive technologies
        can identify them correctly.
        """
        # Email field ARIA label
        try:
            email_el = login_page.find(*LoginPage.EMAIL_INPUT)
            aria_label = email_el.get_attribute("aria-label") or ""
            aria_labelledby = email_el.get_attribute("aria-labelledby") or ""
            associated_label_id = email_el.get_attribute("id") or ""
        except (TimeoutException, WebDriverException) as exc:
            pytest.fail(f"TC_008: Could not inspect email field ARIA attributes: {exc}")

        has_email_aria = bool(aria_label or aria_labelledby or associated_label_id)
        assert has_email_aria, (
            "TC_008: Email input lacks an aria-label, aria-labelledby, or id "
            "for label association."
        )

        # Password field ARIA label
        try:
            pwd_el = login_page.find(*LoginPage.PASSWORD_INPUT)
            pwd_aria_label = pwd_el.get_attribute("aria-label") or ""
            pwd_aria_labelledby = pwd_el.get_attribute("aria-labelledby") or ""
            pwd_id = pwd_el.get_attribute("id") or ""
        except (TimeoutException, WebDriverException) as exc:
            pytest.fail(f"TC_008: Could not inspect password field ARIA attributes: {exc}")

        has_password_aria = bool(pwd_aria_label or pwd_aria_labelledby or pwd_id)
        assert has_password_aria, (
            "TC_008: Password input lacks an aria-label, aria-labelledby, or id "
            "for label association."
        )

        # Submit button role / type
        try:
            submit_el = login_page.find(*LoginPage.SUBMIT_BUTTON)
            btn_role = submit_el.get_attribute("role") or ""
            btn_type = submit_el.get_attribute("type") or ""
            btn_tag = submit_el.tag_name
        except (TimeoutException, WebDriverException) as exc:
            pytest.fail(f"TC_008: Could not inspect submit button ARIA attributes: {exc}")

        is_accessible_button = (
            btn_tag in ("button", "input")
            or btn_role in ("button", "submit")
            or btn_type in ("submit", "button")
        )
        assert is_accessible_button, (
            f"TC_008: Submit element (tag='{btn_tag}', role='{btn_role}', "
            f"type='{btn_type}') does not expose an accessible button role."
        )

    @pytest.mark.a11y
    @pytest.mark.regression
    def test_keyboard_tab_order_follows_logical_sequence(self, login_page):
        """
        Verifies that pressing Tab from the email field moves focus to the
        password field, and a second Tab moves focus to the submit button,
        confirming that focus order follows a logical top-to-bottom sequence.
        """
        try:
            focus_sequence = login_page.tab_through_form()
        except RuntimeError as exc:
            pytest.fail(f"TC_008: Keyboard navigation error: {exc}")

        assert len(focus_sequence) >= 2, (
            f"TC_008: Expected at least 2 focusable elements in the form tab order "
            f"but got {len(focus_sequence)}: {focus_sequence}"
        )

        # First focused element should be the email input
        first_tag, first_identifier = focus_sequence[0]
        assert first_tag in ("input", "textarea"), (
            f"TC_008: First tab-stop should be an input element, got tag='{first_tag}'"
        )

        # Second focused element should be the password input
        second_tag, second_identifier = focus_sequence[1]
        assert second_tag in ("input", "textarea"), (
            f"TC_008: Second tab-stop should be a form input (password), "
            f"got tag='{second_tag}'"
        )

        if len(focus_sequence) >= 3:
            # Third focused element should be the submit button
            third_tag, third_identifier = focus_sequence[2]
            assert third_tag in ("button", "input", "a"), (
                f"TC_008: Third tab-stop should be the submit button, "
                f"got tag='{third_tag}'"
            )

    @pytest.mark.a11y
    @pytest.mark.regression
    def test_submit_button_activatable_via_keyboard(self, login_page):
        """
        Verifies that the submit button can be activated using the Enter key
        when it holds focus, which is required for keyboard-only users.
        Confirms form remains on the page (since no credentials are entered)
        demonstrating the button was triggered.
        """
        try:
            # Navigate to submit button via Tab sequence
            email_el = login_page.find_visible(*LoginPage.EMAIL_INPUT)
            email_el.click()
            email_el.send_keys(Keys.TAB)   # -> password
            active = login_page.get_active_element()
            active.send_keys(Keys.TAB)     # -> submit button
            submit_focused = login_page.get_active_element()

            # Activate with ENTER key
            submit_focused.send_keys(Keys.ENTER)
        except (RuntimeError, WebDriverException) as exc:
            pytest.fail(
                f"TC_008: Failed to activate submit button via keyboard: {exc}"
            )

        # With empty fields the form should either stay on the login page
        # (client-side validation) or show an error — it must NOT navigate away
        # to the dashboard without credentials.
        assert not login_page.is_on_dashboard(), (
            "TC_008: Pressing Enter on the submit button with empty credentials "
            "unexpectedly navigated to the dashboard."
        )