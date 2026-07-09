"""Python client for the SonoVault music metadata API — https://sonovault.now"""

from .client import SonoVault
from .errors import SonoVaultError

__all__ = ["SonoVault", "SonoVaultError"]
__version__ = "1.0.0"
