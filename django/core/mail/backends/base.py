"""Base email backend class."""

from django.core.mail import InvalidEmailProvider
from django.utils.deprecation import RemovedInDjango70Warning, warn_about_external_use


class BaseEmailBackend:
    """
    Base class for email backend implementations.

    Subclasses must implement at least send_messages().

    Subclass __init__() should pass alias and unknown **kwargs to
    super.__init__() for proper error reporting.

    open() and close() can be called indirectly by using a backend object as a
    context manager:

       with backend as connection:
           # do something with connection
           pass
    """

    def __init__(self, *, alias=None, fail_silently=False, **kwargs):
        self.alias = alias
        self.fail_silently = fail_silently

        if kwargs:
            kwarg_names = ", ".join(repr(key) for key in kwargs.keys())
            if alias is not None:
                # Being initialized from mail.providers.
                raise InvalidEmailProvider(
                    f"Unknown OPTIONS {kwarg_names}.", alias=alias
                )
            else:
                # Not being initialized from mail.providers.
                # RemovedInDjango70Warning: replace everything below with:
                #   raise TypeError(
                #       f"Unexpected keyword argument(s) {kwarg_names}."
                #   )

                # Warn when initialized from outside Django, either direct
                # construction of a built-in backend or a super.__init__() call
                # from a non-Django subclass.

                # Count the in-Django subclass __init__() calls to ignore.
                skip_frames = sum(
                    1
                    for cls in type(self).__mro__
                    if (
                        cls is not BaseEmailBackend
                        and cls.__module__.startswith("django.core.mail.backends.")
                        and "__init__" in cls.__dict__
                    )
                )

                # Use something more precise than type(self).__name__, which
                # is often just "EmailBackend".
                class_name = f"{type(self).__module__}.{type(self).__qualname__}"

                warn_about_external_use(
                    f"{class_name}.__init__() does not support {kwarg_names}. "
                    "In Django 7.0, BaseEmailBackend will raise a TypeError "
                    "for unknown keyword arguments.",
                    RemovedInDjango70Warning,
                    skip_frames=skip_frames,
                )

    def open(self):
        """
        Open a network connection.

        This method can be overwritten by backend implementations to
        open a network connection.

        It's up to the backend implementation to track the status of
        a network connection if it's needed by the backend.

        This method can be called by applications to force a single
        network connection to be used when sending mails. See the
        send_messages() method of the SMTP backend for a reference
        implementation.

        The default implementation does nothing.
        """
        pass

    def close(self):
        """Close a network connection."""
        pass

    def __enter__(self):
        try:
            self.open()
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        raise NotImplementedError(
            "subclasses of BaseEmailBackend must override send_messages() method"
        )
