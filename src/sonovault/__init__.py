"""Python client for the SonoVault music metadata API — https://sonovault.now"""

from ._version import __version__
from .client import SonoVault
from .errors import SonoVaultError
from .pagination import paginate
from .webhooks import verify_webhook_signature

__all__ = ["SonoVault", "SonoVaultError", "paginate", "verify_webhook_signature", "__version__"]
