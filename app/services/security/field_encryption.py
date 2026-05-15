from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_PREFIX = "enc::"
ENCRYPTION_VERSION = "v1"
ALGORITHM = "AES-256-GCM"
DEFAULT_KEY_VERSION = "local-kdf-v1"


class EncryptionKeyUnavailableError(RuntimeError):
    pass


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def is_encrypted(value: str | None) -> bool:
    return bool(value and value.startswith(ENVELOPE_PREFIX))


def encrypt_text(plaintext: str | None, key: bytes, key_version: str = DEFAULT_KEY_VERSION) -> str | None:
    if plaintext is None:
        return None
    if plaintext == "":
        return ""
    if is_encrypted(plaintext):
        return plaintext

    nonce = secrets.token_bytes(12)
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    envelope: dict[str, Any] = {
        "version": ENCRYPTION_VERSION,
        "alg": ALGORITHM,
        "nonce": _b64e(nonce),
        "ciphertext": _b64e(ciphertext),
        "key_version": key_version,
    }
    return ENVELOPE_PREFIX + json.dumps(envelope, separators=(",", ":"), ensure_ascii=True)


def decrypt_text(ciphertext: str | None, key: bytes) -> str | None:
    if ciphertext is None:
        return None
    if ciphertext == "":
        return ""
    if not is_encrypted(ciphertext):
        return ciphertext

    payload = json.loads(ciphertext[len(ENVELOPE_PREFIX) :])
    nonce = _b64d(payload["nonce"])
    ct = _b64d(payload["ciphertext"])
    aes = AESGCM(key)
    plaintext = aes.decrypt(nonce, ct, None)
    return plaintext.decode("utf-8")
