from django.core.exceptions import ImproperlyConfigured


class InvalidEmailProvider(ImproperlyConfigured):
    """An email provider's OPTIONS are somehow not valid."""

    def __init__(self, msg, *, alias=None):
        if alias is not None:
            msg = f"EMAIL_PROVIDERS[{alias!r}]: {msg}"
        super().__init__(msg)
