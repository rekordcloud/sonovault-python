"""Webhook signature verification for SonoVault webhook deliveries."""

import hashlib
import hmac
import time
from typing import Union


def verify_webhook_signature(
    secret: str,
    header: str,
    payload: Union[str, bytes],
    tolerance_seconds: int = 300,
) -> bool:
    """Verify a ``SonoVault-Signature`` webhook header against the raw body.

    The header format is ``t=<unix>,v1=<hex>`` where
    ``v1 = HMAC-SHA256(secret, "<t>.<raw body>")``. Use the ``secret``
    returned once by ``sv.webhooks.create()``. Compute over the RAW body
    bytes, before any JSON parsing. Constant-time compare. Rejects
    timestamps outside ``tolerance_seconds`` (default 300; pass 0 to
    disable the age check).

    Example (Flask)::

        @app.post("/webhooks/sonovault")
        def sonovault_webhook():
            ok = verify_webhook_signature(
                secret=os.environ["SONOVAULT_WEBHOOK_SECRET"],
                header=request.headers.get("SonoVault-Signature", ""),
                payload=request.get_data(),
            )
            if not ok:
                abort(400)
            return "", 200
    """
    if not secret or not header:
        return False

    parts = {}
    for kv in header.split(","):
        key, sep, value = kv.partition("=")
        if sep:
            parts[key.strip()] = value.strip()

    try:
        timestamp = int(parts.get("t", ""))
    except ValueError:
        return False
    v1 = parts.get("v1")
    if not v1:
        return False
    if tolerance_seconds > 0 and abs(int(time.time()) - timestamp) > tolerance_seconds:
        return False

    body = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    expected = hmac.new(
        secret.encode("utf-8"), f"{timestamp}.{body}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(v1, expected)
