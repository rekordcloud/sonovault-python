class SonoVaultError(Exception):
    """Raised for any non-2xx API response.

    Attributes:
        status: HTTP status code (0 for network errors).
        body: parsed JSON error body, when the API returned one.
    """

    def __init__(self, message: str, status: int = 0, body=None):
        super().__init__(message)
        self.status = status
        self.body = body

    @property
    def is_auth_error(self) -> bool:
        """Missing or invalid API key."""
        return self.status == 401

    @property
    def is_forbidden(self) -> bool:
        """The endpoint needs a paid tier (or an admin key)."""
        return self.status == 403

    @property
    def is_rate_limited(self) -> bool:
        """Rate limit or monthly credit quota hit."""
        return self.status == 429
