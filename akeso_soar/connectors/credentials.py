"""Fernet-based credential encryption for connector secrets.

The encryption key is read from the ``FERNET_KEY`` environment variable.
If the variable is not set a random key is generated at import time and a
warning is logged (acceptable for local / POC usage).
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

_KEY: bytes | None = None


def _get_fernet() -> Fernet:
    global _KEY
    if _KEY is None:
        env_key = os.environ.get("FERNET_KEY")
        if env_key:
            _KEY = env_key.encode()
        else:
            _KEY = Fernet.generate_key()
            logger.warning(
                "FERNET_KEY not set — generated ephemeral key. "
                "Encrypted credentials will NOT survive restarts."
            )
    return Fernet(_KEY)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def encrypt_credential(plaintext: str) -> str:
    """Encrypt *plaintext* and return a URL-safe base-64 encoded string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a previously encrypted *ciphertext* string.

    Raises ``ValueError`` if the token is invalid or tampered with.
    """
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt credential — invalid or corrupted token") from exc
