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
# Configuration constants (mirror what conftest.py would expose)
# ---------------------------------------------------------------------------
BASE_URL = "https://www.google.com"
DEFAULT_TIMEOUT = 10
LOGIN_PATH = "/login"
DASHBOARD_PATH = "/dashboard"


# ===========================================================================
# Base Page
# ===========================================================================
class BasePage:
    """Shared helpers for all Page Object classes."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def navigate(self, path: str) -> None:
        """Navigate to a path relative to BASE_URL."""
        try:
            self.driver.get(f"{BASE_URL}{path}")
        except WebDriverException as exc:
            raise RuntimeError(f"Failed to navigate to '{path}': {exc}") from exc

    def find(self, by: str, value: str):
        """Wait for an element to be present in the DOM and return it."""
        try:
            return self.wait.until(
                EC.presence_of_element_located((by, value)),
                message=f"Element not found — locator: ({by}, '{value}')",
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
                message=f"Element not visible — locator: ({by}, '{value}')",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for visible element ({by}, '{value}')"
            ) from exc

    def click(self, by: str, value: str) -> None:
        """Wait for an element to be clickable and click it."""
        try:
            element = self.wait.until(
                EC.element_to_be_clickable((by, value)),
                message=f"Element not clickable — locator: ({by}, '{value}')",
            )
            element.click()
        except TimeoutException as exc:
            raise TimeoutException(
                f"Timed out waiting for clickable element ({by}, '{value}')"
            ) from exc
        except WebDriverException as exc:
            raise RuntimeError(
                f"Click failed on element ({by}, '{value}'): {exc}"
            ) from exc

    def type_text(self, by: str, value: str, text: str) -> None:
        """Clear a field and type text into it."""
        try:
            element = self.find_visible(by, value)
            element.clear()
            if text:
                element.send_keys(text)
        except WebDriverException as exc:
            raise RuntimeError(
                f"Failed to type into element ({by}, '{value}'): {exc}"
            ) from exc

    def get_text(self, by: str, value: str) -> str:
        """Return the visible text of an element."""
        try:
            return self.find_visible(by, value).text
        except WebDriverException as exc:
            raise RuntimeError(
                f"Failed to get text from element ({by}, '{value}'): {exc}"
            ) from exc

    def is_element_present(self, by: str, value: str) -> bool:
        """Return True if the element exists in the DOM within the timeout."""
        try:
            self.wait.until(EC.presence_of_element_located((by, value)))
            return True
        except TimeoutException:
            return False

    def is_element_visible(self, by: str, value: str) -> bool:
        """Return True if the element is visible within the timeout."""
        try:
            self.wait.until(EC.visibility_of_element_located((by, value)))
            return True
        except TimeoutException:
            return False

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

    def get_attribute(self, by: str, value: str, attribute: str) -> str:
        """Return an attribute value from the located element."""
        try:
            element = self.find(by, value)
            return element.get_attribute(attribute)
        except WebDriverException as exc:
            raise RuntimeError(
                f"Failed to get attribute '{attribute}' from ({by}, '{value}'): {exc}"
            ) from exc


# ===========================================================================
# Login Page Object
# ===========================================================================
class LoginPage(BasePage):
    """Page Object for the Login page."""

    # Locators — preference: data-testid > ARIA > CSS > XPath
    EMAIL_INPUT = (By.CSS_SELECTOR, '[data-testid="email"]')
    PASSWORD_INPUT = (By.CSS_SELECTOR, '[data-testid="password"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"]')

    # Error / validation message locators
    AUTH_ERROR = (By.CSS_SELECTOR, '[data-testid="auth-error"]')
    EMAIL_ERROR = (By.CSS_SELECTOR, '[data-testid="email-error"]')
    PASSWORD_ERROR = (By.CSS_SELECTOR, '[data-testid="password-error"]')

    # Fallback ARIA-based locators used in accessibility checks
    EMAIL_LABEL = (By.XPATH, '//label[@for="email" or contains(@id,"email-label")]')
    PASSWORD_LABEL = (
        By.XPATH,
        '//label[@for="password" or contains(@id,"password-label")]',
    )
    ARIA_LIVE_REGION = (By.CSS_SELECTOR, '[aria-live]')

    def open(self) -> "LoginPage":
        """Navigate to the login page and wait for the email field to appear."""
        self.navigate(LOGIN_PATH)
        self.find_visible(*self.EMAIL_INPUT)
        return self

    # ------------------------------------------------------------------
    # Form interaction helpers
    # ------------------------------------------------------------------
    def enter_email(self, email: str) -> "LoginPage":
        """Type *email* into the email field."""
        self.type_text(*self.EMAIL_INPUT, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Type *password* into the password field."""
        self.type_text(*self.PASSWORD_INPUT, password)
        return self

    def submit(self) -> "LoginPage":
        """Click the submit button."""
        self.click(*self.SUBMIT_BUTTON)
        return self

    def login(self, email: str, password: str) -> "LoginPage":
        """Fill in the login form and submit it."""
        self.enter_email(email)
        self.enter_password(password)
        self.submit()
        return self

    # ------------------------------------------------------------------
    # State inspection helpers
    # ------------------------------------------------------------------
    def is_on_login_page(self) -> bool:
        """Return True if the current URL still points to the login page."""
        return LOGIN_PATH in self.driver.current_url

    def is_on_dashboard(self) -> bool:
        """Return True if the current URL contains the dashboard path."""
        return DASHBOARD_PATH in self.driver.current_url

    def auth_error_is_displayed(self) -> bool:
        """Return True if the authentication error message is visible."""
        return self.is_element_visible(*self.AUTH_ERROR)

    def email_error_is_displayed(self) -> bool:
        """Return True if the email validation error is visible."""
        return self.is_element_visible(*self.EMAIL_ERROR)

    def password_error_is_displayed(self) -> bool:
        """Return True if the password validation error is visible."""
        return self.is_element_visible(*self.PASSWORD_ERROR)

    def get_auth_error_text(self) -> str:
        """Return the text of the authentication error message."""
        return self.get_text(*self.AUTH_ERROR)

    def get_email_error_text(self) -> str:
        """Return the text of the email validation error message."""
        return self.get_text(*self.EMAIL_ERROR)

    def get_password_error_text(self) -> str:
        """Return the text of the password validation error message."""
        return self.get_text(*self.PASSWORD_ERROR)

    def get_password_field_type(self) -> str:
        """Return the *type* attribute of the password input element."""
        return self.get_attribute(*self.PASSWORD_INPUT, "type")

    def email_has_accessible_label(self) -> bool:
        """Return True if the email input has an associated accessible label."""
        try:
            email_el = self.find(*self.EMAIL_INPUT)
            field_id = email_el.get_attribute("id") or ""
            aria_label = email_el.get_attribute("aria-label") or ""
            aria_labelledby = email_el.get_attribute("aria-labelledby") or ""
            if aria_label or aria_labelledby:
                return True
            if field_id:
                labels = self.driver.find_elements(
                    By.CSS_SELECTOR, f'label[for="{field_id}"]'
                )
                return len(labels) > 0
            return False
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not inspect accessible label for email field: {exc}"
            ) from exc

    def password_has_accessible_label(self) -> bool:
        """Return True if the password input has an associated accessible label."""
        try:
            pwd_el = self.find(*self.PASSWORD_INPUT)
            field_id = pwd_el.get_attribute("id") or ""
            aria_label = pwd_el.get_attribute("aria-label") or ""
            aria_labelledby = pwd_el.get_attribute("aria-labelledby") or ""
            if aria_label or aria_labelledby:
                return True
            if field_id:
                labels = self.driver.find_elements(
                    By.CSS_SELECTOR, f'label[for="{field_id}"]'
                )
                return len(labels) > 0
            return False
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not inspect accessible label for password field: {exc}"
            ) from exc

    def submit_button_is_keyboard_focusable(self) -> bool:
        """Return True if the submit button can receive keyboard focus (tabindex >= 0)."""
        try:
            btn = self.find(*self.SUBMIT_BUTTON)
            tabindex = btn.get_attribute("tabindex")
            # tabindex=None means natural tab order (focusable); "-1" means excluded
            return tabindex != "-1"
        except (NoSuchElementException, WebDriverException) as exc:
            raise RuntimeError(
                f"Could not inspect tabindex on submit button: {exc}"
            ) from exc

    def aria_live_region_exists(self) -> bool:
        """Return True if at least one aria-live region is present in the DOM."""
        try:
            regions = self.driver.find_elements(*self.ARIA_LIVE_REGION)
            return len(regions) > 0
        except WebDriverException as exc:
            raise RuntimeError(
                f"Could not inspect ARIA live regions: {exc}"
            ) from exc

    def navigate_to_email_via_tab(self) -> None:
        """Focus the email field by clicking it — simulates initial Tab focus entry."""
        try:
            self.find_visible(*self.EMAIL_INPUT).click()
        except WebDriverException as exc:
            raise RuntimeError(f"Could not focus email field via click: {exc}") from exc

    def tab_to_next_field(self) -> None:
        """Send Tab from the currently active element to move to the next focusable element."""
        try:
            self.driver.switch_to.active_element.send_keys(Keys.TAB)
        except WebDriverException as exc:
            raise RuntimeError(f"Could not send TAB key: {exc}") from exc

    def press_enter_on_active_element(self) -> None:
        """Send Enter from the currently focused element."""
        try:
            self.driver.switch_to.active_element.send_keys(Keys.ENTER)
        except WebDriverException as exc:
            raise RuntimeError(f"Could not send ENTER key: {exc}") from exc

    def active_element_matches(self, by: str, value: str) -> bool:
        """Return True if the currently focused element matches the given locator."""
        try:
            expected = self.find(by, value)
            active = self.driver.switch_to.active_element
            return expected == active
        except WebDriverException:
            return False


# ===========================================================================
# Dashboard Page Object (lightweight — only used to verify redirect)
# ===========================================================================
class DashboardPage(BasePage):
    """Minimal Page Object for the Dashboard page."""

    DASHBOARD_HEADING = (
        By.XPATH,
        '//*[@data-testid="dashboard-heading" or @role="heading"]',
    )
    ERROR_MESSAGES = (By.CSS_SELECTOR, '[data-testid="error-message"], .error-message')

    def is_loaded(self) -> bool:
        """Return True if the dashboard page has loaded."""
        return DASHBOARD_PATH in self.driver.current_url

    def has_no_error_messages(self) -> bool:
        """Return True when no error-message elements are visible on the page."""
        try:
            errors = self.driver.find_elements(*self.ERROR_MESSAGES)
            visible_errors = [e for e in errors if e.is_displayed()]
            return len(visible_errors) == 0
        except WebDriverException as exc:
            raise RuntimeError(
                f"Could not query error messages on dashboard: {exc}"
            ) from exc


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def login_page(driver):
    """Return a LoginPage instance pointed at the login URL."""
    page = LoginPage(driver)
    page.open()
    return page


@pytest.fixture
def dashboard_page(driver):
    """Return a DashboardPage instance (no navigation — caller must be on the page)."""
    return DashboardPage(driver)


# ===========================================================================
# TC_001 — Successful login navigates to dashboard
# ===========================================================================
@pytest.mark.smoke
@pytest.mark.regression
class TestTC001SuccessfulLogin:
    def test_valid_credentials_redirect_to_dashboard(self, login_page, dashboard_page):
        """TC_001: Verify that submitting valid credentials redirects the user to
        the dashboard and that no error messages are present on arrival.

        Given the user is on the login page,
        When they submit valid email and password,
        Then they are redirected to /dashboard with no error messages displayed.
        """
        email = "admin@test.com"
        password = "correct_pass"

        try:
            login_page.login(email, password)
            login_page.wait_for_url_contains(DASHBOARD_PATH)
        except TimeoutException as exc:
            pytest.fail(
                f"TC_001: Dashboard URL was not reached after valid login. "
                f"Current URL: {login_page.driver.current_url}. Detail: {exc}"
            )

        assert dashboard_page.is_loaded(), (
            f"TC_001: Expected URL to contain '{DASHBOARD_PATH}', "
            f"got '{dashboard_page.driver.current_url}'"
        )
        assert dashboard_page.has_no_error_messages(), (
            "TC_001: Error messages were unexpectedly displayed on the dashboard."
        )


# ===========================================================================
# TC_002 — Incorrect password shows authentication error
# ===========================================================================
@pytest.mark.regression
class TestTC002IncorrectPassword:
    def test_wrong_password_shows_auth_error(self, login_page):
        """TC_002: Verify that an incorrect password blocks login, keeps the user
        on the login page, and displays an authentication error message.

        Given the user is on the login page,
        When they enter a valid email with a wrong password and submit,
        Then the login page remains visible and an auth error is shown.
        """
        email = "admin@test.com"
        password = "wrong_pass"

        login_page.login(email, password)

        assert login_page.is_on_login_page(), (
            f"TC_002: Expected to remain on login page but URL is "
            f"'{login_page.driver.current_url}'"
        )
        assert login_page.auth_error_is_displayed(), (
            "TC_002: Authentication error message was not displayed for wrong password."
        )


# ===========================================================================
# TC_003 — Malformed email shows format validation error
# ===========================================================================
@pytest.mark.regression
class TestTC003MalformedEmail:
    def test_malformed_email_shows_format_error(self, login_page):
        """TC_003: Verify that a malformed email prevents form submission and
        triggers an email format validation error message.

        Given the user is on the login page,
        When they enter a malformed email address and submit,
        Then the form is not submitted and an email format error is shown.
        """
        email = "not-an-email"
        password = "correct_pass"

        login_page.login(email, password)

        assert login_page.is_on_login_page(), (
            f"TC_003: Form should not have been submitted. "
            f"URL changed to '{login_page.driver.current_url}'"
        )
        assert login_page.email_error_is_displayed(), (
            "TC_003: Email format validation error was not displayed."
        )


# ===========================================================================
# TC_004 — Empty password shows required-field error for password only
# ===========================================================================
@pytest.mark.regression
class TestTC004EmptyPassword:
    def test_empty_password_shows_password_required_error(self, login_page):
        """TC_004: Verify that leaving the password field empty prevents submission
        and shows a required-field error for the password field only — the email
        field must not display an error.

        Given the user is on the login page,
        When they enter a valid email, leave password empty, and submit,
        Then only the password required-field error is shown.
        """
        email = "admin@test.com"
        password = ""

        login_page.login(email, password)

        assert login_page.is_on_login_page(), (
            f"TC_004: Form should not have been submitted. "
            f"URL changed to '{login_page.driver.current_url}'"
        )
        assert login_page.password_error_is_displayed(), (
            "TC_004: Required-field error for password was not displayed."
        )
        assert not login_page.email_error_is_displayed(), (
            "TC_004: Email error should NOT be displayed when only password is empty."
        )


# ===========================================================================
# TC_005 — Both fields empty shows required-field errors for both
# ===========================================================================
@pytest.mark.regression
class TestTC005BothFieldsEmpty:
    def test_both_fields_empty_shows_both_required_errors(self, login_page):
        """TC_005: Verify that leaving both email and password empty prevents
        form submission and triggers required-field errors for both fields.

        Given the user is on the login page,
        When they leave both fields empty and click submit,
        Then required-field errors are shown for both email and password.
        """
        login_page.login("", "")

        assert login_page.is_on_login_page(), (
            f"TC_005: Form should not have been submitted. "
            f"URL changed to '{login_page.driver.current_url}'"
        )
        assert login_page.email_error_is_displayed(), (
            "TC_005: Required-field error for email was not displayed."
        )
        assert login_page.password_error_is_displayed(), (
            "TC_005: Required-field error for password was not displayed."
        )


# ===========================================================================
# TC_006 — Unregistered email shows generic authentication error
# ===========================================================================
@pytest.mark.regression
class TestTC006UnregisteredEmail:
    def test_unregistered_email_shows_generic_auth_error(self, login_page):
        """TC_006: Verify that an unregistered email address blocks login, keeps
        the user on the login page, and shows a generic authentication error that
        does not reveal whether the email exists in the system.

        Given the user is on the login page,
        When they submit with a non-existent email,
        Then the login page remains visible and a generic auth error is shown.
        """
        email = "nonexistent@test.com"
        password = "any_pass"

        login_page.login(email, password)

        assert login_page.is_on_login_page(), (
            f"TC_006: Expected to remain on login page but URL is "
            f"'{login_page.driver.current_url}'"
        )
        assert login_page.auth_error_is_displayed(), (
            "TC_006: Authentication error message was not displayed for unregistered email."
        )

        error_text = login_page.get_auth_error_text().lower()
        revealing_phrases = ["email not found", "no account", "does not exist", "not registered"]
        for phrase in revealing_phrases:
            assert phrase not in error_text, (
                f"TC_006: Error message reveals email existence via phrase '{phrase}'. "
                f"Full message: '{error_text}'"
            )


# ===========================================================================
# TC_007 — Keyboard navigation and ARIA accessibility
# ===========================================================================
@pytest.mark.a11y
@pytest.mark.regression
class TestTC007KeyboardAndAria:
    def test_form_is_keyboard_navigable_and_has_aria_attributes(self, login_page):
        """TC_007: Verify that the login form is fully operable via keyboard-only
        navigation and that all elements carry correct ARIA attributes.

        Given the user is on the login page,
        When they navigate using Tab and Enter keys,
        Then every interactive element is reachable and operable, each input has
        an accessible label, and error messages are surfaced via ARIA live regions.
        """
        # Step 1: Focus the email field (entry point for keyboard navigation)
        try:
            login_page.navigate_to_email_via_tab()
        except RuntimeError as exc:
            pytest.fail(f"TC_007: Could not focus email input: {exc}")

        assert login_page.active_element_matches(*LoginPage.EMAIL_INPUT), (
            "TC_007: Email field is not the active element after initial focus."
        )

        # Step 2: Tab to password field
        try:
            login_page.tab_to_next_field()
        except RuntimeError as exc:
            pytest.fail(f"TC_007: TAB from email to password failed: {exc}")

        assert login_page.active_element_matches(*LoginPage.PASSWORD_INPUT), (
            "TC_007: Password field is not focused after pressing Tab from email."
        )

        # Step 3: Tab to submit button
        try:
            login_page.tab_to_next_field()
        except RuntimeError as exc:
            pytest.fail(f"TC_007: TAB from password to submit failed: {exc}")

        assert login_page.active_element_matches(*LoginPage.SUBMIT_BUTTON), (
            "TC_007: Submit button is not focused after pressing Tab from password."
        )

        # Step 4: Verify submit button is keyboard-operable
        assert login_page.submit_button_is_keyboard_focusable(), (
            "TC_007: Submit button has tabindex='-1' and cannot be reached via Tab."
        )

        # Step 5: Check accessible labels
        assert login_page.email_has_accessible_label(), (
            "TC_007: Email input lacks an accessible label (aria-label, aria-labelledby, or <label for>)."
        )
        assert login_page.password_has_accessible_label(), (
            "TC_007: Password input lacks an accessible label (aria-label, aria-labelledby, or <label for>)."
        )

        # Step 6: Trigger validation by submitting empty fields, then check live region
        login_page.open()  # reset form state
        login_page.submit()
        assert login_page.aria_live_region_exists(), (
            "TC_007: No aria-live region found — assistive technologies cannot announce errors."
        )


# ===========================================================================
# TC_008 — Password field masks input
# ===========================================================================
@pytest.mark.regression
class TestTC008PasswordMasking:
    def test_password_field_type_is_password_and_masks_input(self, login_page):
        """TC_008: Verify that the password input field has type='password' so
        that entered characters are masked and not displayed in plain text.

        Given the user is on the login page,
        When they type a password into the password field,
        Then the field's type attribute is 'password' and characters are masked.
        """
        password = "secret_pass"

        try:
            login_page.enter_password(password)
        except RuntimeError as exc:
            pytest.fail(f"TC_008: Could not enter password: {exc}")

        field_type = login_page.get_password_field_type()

        assert field_type == "password", (
            f"TC_008: Password field type should be 'password' but is '{field_type}'. "
            "Characters may be visible in plain text."
        )


# ===========================================================================
# Data-driven parametrised companion test covering TC_001 / TC_002 / TC_006
# ===========================================================================
@pytest.mark.parametrize(
    "email,password,expect_dashboard,expect_auth_error,test_id",
    [
        (
            "admin@test.com",
            "correct_pass",
            True,
            False,
            "valid_credentials",
        ),
        (
            "admin@test.com",
            "wrong_pass",
            False,
            True,
            "wrong_password",
        ),
        (
            "nonexistent@test.com",
            "any_pass",
            False,
            True,
            "unregistered_email",
        ),
    ],
)
def test_login_authentication_variants(
    login_page,
    dashboard_page,
    email,
    password,
    expect_dashboard,
    expect_auth_error,
    test_id,
):
    """Parametrised data-driven test covering successful login (TC_001),
    wrong-password rejection (TC_002), and unregistered-email rejection (TC_006).

    For each combination the test verifies:
    - Whether the user lands on the dashboard or remains on the login page.
    - Whether an authentication error is displayed (or not).
    """
    try:
        login_page.login(email, password)
    except RuntimeError as exc:
        pytest.fail(f"[{test_id}] Login interaction failed: {exc}")

    if expect_dashboard:
        try:
            login_page.wait_for_url_contains(DASHBOARD_PATH)
        except TimeoutException as exc:
            pytest.fail(
                f"[{test_id}] Expected redirect to dashboard but stayed on "
                f"'{login_page.driver.current_url}': {exc}"
            )
        assert dashboard_page.is_loaded(), (
            f"[{test_id}] Dashboard page is not loaded. "
            f"Current URL: {dashboard_page.driver.current_url}"
        )
        assert dashboard_page.has_no_error_messages(), (
            f"[{test_id}] Unexpected error messages found on the dashboard."
        )
    else:
        assert login_page.is_on_login_page(), (
            f"[{test_id}] User should remain on the login page. "
            f"Current URL: '{login_page.driver.current_url}'"
        )

    if expect_auth_error:
        assert login_page.auth_error_is_displayed(), (
            f"[{test_id}] Expected an authentication error message but none was found."
        )
    else:
        assert not login_page.auth_error_is_displayed(), (
            f"[{test_id}] No authentication error should appear after successful login."
        )