# RemovedInDjango70Warning: This entire file.
import types
import warnings
from email.mime.text import MIMEText
from unittest import mock

from django.conf import LazySettings, settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import (
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
)
from django.core.mail.message import forbid_multi_line_headers, sanitize_address
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango70Warning

from .tests import MailTestsMixin


class DeprecationWarningTests(MailTestsMixin, SimpleTestCase):
    def test_deprecated_on_import(self):
        """
        These items are not typically called from user code,
        so generate deprecation warnings immediately at the time
        they are imported from django.core.mail.
        """
        cases = [
            # name, msg
            (
                "BadHeaderError",
                "BadHeaderError is deprecated. Replace with ValueError.",
            ),
            (
                "SafeMIMEText",
                "SafeMIMEText is deprecated. The return value of"
                " EmailMessage.message() is an email.message.EmailMessage.",
            ),
            (
                "SafeMIMEMultipart",
                "SafeMIMEMultipart is deprecated. The return value of"
                " EmailMessage.message() is an email.message.EmailMessage.",
            ),
        ]
        for name, msg in cases:
            with self.subTest(name=name):
                with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
                    __import__("django.core.mail", fromlist=[name])

    def test_sanitize_address_deprecated(self):
        msg = (
            "The internal API sanitize_address() is deprecated."
            " Python's modern email API (with email.message.EmailMessage or"
            " email.policy.default) will handle most required validation and"
            " encoding. Use Python's email.headerregistry.Address to construct"
            " formatted addresses from component parts."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            sanitize_address("to@example.com", "ascii")

    def test_forbid_multi_line_headers_deprecated(self):
        msg = (
            "The internal API forbid_multi_line_headers() is deprecated."
            " Python's modern email API (with email.message.EmailMessage or"
            " email.policy.default) will reject multi-line headers."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            forbid_multi_line_headers("To", "to@example.com", "ascii")


class UndocumentedFeatureErrorTests(SimpleTestCase):
    """
    These undocumented features were removed without going through deprecation.
    In case they were being used, they now raise errors.
    """

    def test_undocumented_mixed_subtype(self):
        """
        Trying to use the previously undocumented, now unsupported
        EmailMessage.mixed_subtype causes an error.
        """
        msg = (
            "EmailMessage no longer supports"
            " the undocumented `mixed_subtype` attribute"
        )
        email = EmailMessage(
            attachments=[EmailAttachment(None, b"GIF89a...", "image/gif")]
        )
        email.mixed_subtype = "related"
        with self.assertRaisesMessage(AttributeError, msg):
            email.message()

    def test_undocumented_alternative_subtype(self):
        """
        Trying to use the previously undocumented, now unsupported
        EmailMultiAlternatives.alternative_subtype causes an error.
        """
        msg = (
            "EmailMultiAlternatives no longer supports"
            " the undocumented `alternative_subtype` attribute"
        )
        email = EmailMultiAlternatives(
            alternatives=[EmailAlternative("", "text/plain")]
        )
        email.alternative_subtype = "multilingual"
        with self.assertRaisesMessage(AttributeError, msg):
            email.message()

    def test_undocumented_get_connection_override(self):
        """
        Trying to define a get_connection() method on an EmailMessage subclass
        causes an error (because the base class no longer calls that method).
        """

        class CustomEmailMessage(EmailMessage):
            def get_connection(self, fail_silently=False):
                return None

        email = CustomEmailMessage(to=["to@example.com"])

        msg = (
            "EmailMessage no longer supports the undocumented "
            "get_connection() method."
        )
        with self.assertRaisesMessage(AttributeError, msg):
            email.send()


@ignore_warnings(category=RemovedInDjango70Warning)
class DeprecatedCompatibilityTests(SimpleTestCase):
    def test_bad_header_error(self):
        """
        Existing code that catches deprecated BadHeaderError should be
        compatible with modern email (which raises ValueError instead).
        """
        from django.core.mail import BadHeaderError

        with self.assertRaises(BadHeaderError):
            EmailMessage(subject="Bad\r\nHeader").message()

    def test_attachments_mimebase_in_constructor(self):
        txt = MIMEText("content1")
        msg = EmailMessage(attachments=[txt])
        payload = msg.message().get_payload()
        self.assertEqual(payload[0], txt)


class DeprecatedEmailSettingsTests(SimpleTestCase):
    """
    Deprecation warnings and compatibility errors related to EMAIL_PROVIDERS.
    """

    DEPRECATED_SETTING_DEFAULTS = {
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "localhost",
        "EMAIL_PORT": 25,
        "EMAIL_HOST_USER": "",
        "EMAIL_HOST_PASSWORD": "",
        "EMAIL_USE_TLS": False,
        "EMAIL_USE_SSL": False,
        "EMAIL_SSL_CERTFILE": None,
        "EMAIL_SSL_KEYFILE": None,
        "EMAIL_TIMEOUT": None,
        # EMAIL_FILE_PATH does not have a default.
    }

    DEPRECATED_SETTINGS = DEPRECATED_SETTING_DEFAULTS.keys() | {"EMAIL_FILE_PATH"}

    def init_settings(self):
        """Simulate fresh initialization of django.conf.settings."""
        settings = LazySettings()
        getattr(settings, "FOO", None)  # Trigger _setup().
        return settings

    def mock_settings_module(self, **settings):
        """
        Create an in-memory settings "module" that will be read by the next
        Settings.__init__() (or LazySettings._setup()). (This does not affect
        django.conf.settings if it has already been initialized.)
        """
        settings_module = types.ModuleType("mocked_settings")
        for name, value in settings.items():
            setattr(settings_module, name, value)
        return mock.patch(
            "django.conf.importlib.import_module",
            autospec=True,
            return_value=settings_module,
        )

    def test_warn_when_defining_deprecated_settings(self):
        """Warn on init if deprecated settings are defined."""
        for name in self.DEPRECATED_SETTINGS:
            msg = (
                f"The {name} setting is deprecated. Migrate to "
                "EMAIL_PROVIDERS before Django 7.0."
            )
            settings = {name: "foo"}
            with self.subTest(name=name):
                with (
                    self.subTest("settings module"),
                    self.mock_settings_module(**settings),
                    self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                ):
                    self.init_settings()
                with (
                    self.subTest("settings.configure()"),
                    self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                ):
                    LazySettings().configure(**settings)

        # Multiple deprecated settings are reported all at once.
        with self.subTest("multiple settings"):
            msg = (
                "The EMAIL_BACKEND, EMAIL_HOST settings are deprecated. "
                "Migrate to EMAIL_PROVIDERS before Django 7.0."
            )
            settings = {"EMAIL_BACKEND": "foo", "EMAIL_HOST": "bar"}
            with (
                self.subTest("settings module"),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                self.mock_settings_module(**settings),
            ):
                self.init_settings()
            with (
                self.subTest("settings.configure()"),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ):
                LazySettings().configure(**settings)

    def test_warn_email_providers_will_be_empty(self):
        """
        If no email-related settings are defined, warn that EMAIL_PROVIDERS
        will be needed in Django 7.0.
        """
        msg = (
            "Django 7.0 will not have a default email provider. "
            "Define EMAIL_PROVIDERS in your settings to configure email."
        )
        with (
            self.subTest("settings module"),
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
        ):
            self.init_settings()

        with (
            self.subTest("settings.configure()"),
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
        ):
            LazySettings().configure()

    def test_no_warning_if_any_email_setting_defined(self):
        """
        The warning from the previous test is _not_ emitted when either
        EMAIL_PROVIDERS or a deprecated setting is defined.
        """
        msg = "Django 7.0 will not have a default email provider."
        for name in self.DEPRECATED_SETTINGS | {"EMAIL_PROVIDERS"}:
            with (
                self.subTest(name=name),
                self.mock_settings_module(**{name: "foo"}),
                # Use catch_warnings() to implement the equivalent of:
                #   self.assertNotWarnsMessage(msg, RemovedInDjango70Warning)
                warnings.catch_warnings(
                    category=RemovedInDjango70Warning, record=True
                ) as caught_warnings,
            ):
                # runtests.py filters this exact warning (to avoid it breaking
                # all tests). Undo that filter.
                warnings.simplefilter("always", category=RemovedInDjango70Warning)

                self.init_settings()

                warning_messages = [str(w.message) for w in caught_warnings or []]
                found = any(msg in w for w in warning_messages)
                self.assertFalse(found, f"{msg!r} was found in {warning_messages!r}.")

    def test_error_on_conflicting_settings(self):
        """EMAIL_PROVIDERS conflicts with deprecated email settings."""
        for name in self.DEPRECATED_SETTINGS:
            msg = (
                f"The deprecated {name} setting is not allowed when "
                "EMAIL_PROVIDERS is defined."
            )
            settings = {name: "foo", "EMAIL_PROVIDERS": {}}
            with self.subTest(name=name):
                with (
                    self.subTest("settings module"),
                    self.mock_settings_module(**settings),
                    self.assertRaisesMessage(ImproperlyConfigured, msg),
                ):
                    self.init_settings()
                with (
                    self.subTest("settings.configure()"),
                    self.assertRaisesMessage(ImproperlyConfigured, msg),
                ):
                    LazySettings().configure(**settings)

        # Multiple incompatible settings are reported all at once.
        with self.subTest("multiple settings"):
            msg = (
                "The deprecated EMAIL_BACKEND, EMAIL_HOST settings are not "
                "allowed when EMAIL_PROVIDERS is defined."
            )
            settings = {
                "EMAIL_BACKEND": "foo",
                "EMAIL_HOST": "bar",
                "EMAIL_PROVIDERS": {},
            }
            with (
                self.subTest("settings module"),
                self.assertRaisesMessage(ImproperlyConfigured, msg),
                self.mock_settings_module(**settings),
            ):
                self.init_settings()
            with (
                self.subTest("settings.configure()"),
                self.assertRaisesMessage(ImproperlyConfigured, msg),
            ):
                LazySettings().configure(**settings)

    def test_warning_on_access(self):
        """Warn when trying to use any deprecated setting."""
        for name in self.DEPRECATED_SETTINGS:
            msg = (
                f"The {name} setting is deprecated. Migrate to "
                "EMAIL_PROVIDERS before Django 7.0."
            )
            with (
                self.subTest(name=name),
                self.settings(**{name: "foo"}),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ):
                getattr(settings, name)

    @override_settings(EMAIL_PROVIDERS={})
    def test_hasattr(self):
        """Deprecated settings are not defined when EMAIL_PROVIDERS is."""
        for name in self.DEPRECATED_SETTINGS:
            with self.subTest(name=name):
                self.assertFalse(hasattr(settings, name))

    @override_settings(EMAIL_PROVIDERS={})
    def test_deprecated_settings_not_in_dir_with_email_providers(self):
        """
        When EMAIL_PROVIDERS is defined, the global_settings defaults for the
        deprecated settings aren't included in dir(settings).
        """
        known_settings = dir(settings)
        actual_overlap = set(self.DEPRECATED_SETTINGS) & set(known_settings)
        self.assertEqual(actual_overlap, set())

    def test_deprecated_settings_are_in_dir_without_email_providers(self):
        expected_settings = self.DEPRECATED_SETTING_DEFAULTS.keys()
        known_settings = dir(settings)
        actual_overlap = set(expected_settings) & set(known_settings)
        self.assertEqual(actual_overlap, expected_settings)

    @override_settings(EMAIL_PROVIDERS={})
    def test_error_on_conflicting_access(self):
        """
        Trying to access a deprecated setting becomes an error when
        EMAIL_PROVIDERS is defined.
        """
        for name in self.DEPRECATED_SETTINGS:
            msg = (
                f"The {name} setting is not available when EMAIL_PROVIDERS "
                "is defined"
            )
            with self.subTest(name=name), self.settings(**{name: "foo"}):
                with self.assertRaisesMessage(AttributeError, msg):
                    getattr(settings, name)

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_direct_settings_manipulation(self):
        """
        Errors are conflicting access are enforced when directly manipulating
        settings after initialization.
        """
        settings = self.init_settings()

        # Accessing setting caches its value in LazySettings.__dir__.
        self.assertEqual(settings.EMAIL_PORT, 25)

        # Defining EMAIL_PROVIDERS invalidates the cache but is not an error.
        settings.EMAIL_PROVIDERS = {}

        # Accessing the conflicting setting _is_ an error.
        msg = "not available when EMAIL_PROVIDERS is defined"
        with self.assertRaisesMessage(AttributeError, msg):
            _ = settings.EMAIL_PORT  # Not `25` from the cache.

        # Adding a conflicting setting is not an error, but accessing it is.
        settings.EMAIL_HOST = "example.com"
        with self.assertRaisesMessage(AttributeError, msg):
            _ = settings.EMAIL_HOST

        # Deleting EMAIL_PROVIDERS removes the conflict and allows access to
        # the deprecated settings again.
        del settings.EMAIL_PROVIDERS
        self.assertEqual(settings.EMAIL_PORT, 25)
        self.assertEqual(settings.EMAIL_HOST, "example.com")

    def test_override_settings_conflicts(self):
        """
        Although override_settings() doesn't block _defining_ settings that
        conflict with EMAIL_PROVIDERS, errors still apply on _access_.
        """
        with (
            override_settings(EMAIL_PROVIDERS={}),
            override_settings(EMAIL_HOST="example.com"),
        ):
            self.assertEqual(settings.EMAIL_PROVIDERS, {})
            with self.assertRaisesMessage(AttributeError, "not available"):
                _ = settings.EMAIL_HOST

            # The conflicting settings are defined (not inherited from default
            # global_settings), so both appear in LazySettings.__dir__().
            self.assertIn("EMAIL_HOST", dir(settings))
            self.assertIn("EMAIL_PROVIDERS", dir(settings))

            del settings.EMAIL_HOST
            self.assertNotIn("EMAIL_HOST", dir(settings))

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_defaults_unchanged(self):
        """Deprecated settings have the same defaults as earlier releases."""
        # Django's test runner overrides EMAIL_BACKEND in django.conf.settings,
        # so construct a fresh settings object for this test.
        settings = self.init_settings()
        for name, expected in self.DEPRECATED_SETTING_DEFAULTS.items():
            with self.subTest(name=name):
                actual = getattr(settings, name)
                if expected is None:
                    self.assertIsNone(actual)
                elif expected is True or expected is False:
                    self.assertIs(actual, expected)
                else:
                    self.assertEqual(actual, expected)

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_email_backend_override_during_tests(self):
        self.assertEqual(
            settings.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend"
        )
