"""Python client for the SonoVault music metadata API — https://sonovault.now"""

from .client import SonoVault
from .errors import SonoVaultError
from .webhooks import verify_webhook_signature

__all__ = ["SonoVault", "SonoVaultError", "verify_webhook_signature"]
__version__ = "1.0.0"
