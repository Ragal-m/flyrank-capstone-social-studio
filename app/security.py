import base64
import hashlib
import hmac
import json
import os
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .settings import get_settings


def encryption_key() -> bytes:
    configured = get_settings().encryption_key
    if configured:
        key = base64.b64decode(configured)
        if len(key) != 32:
            raise ValueError("ENCRYPTION_KEY must decode to 32 bytes")
        return key
    return hashlib.sha256(b"local-development-key").digest()


def encrypt_token(token: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(encryption_key()).encrypt(nonce, token.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_token(value: str) -> str:
    decoded = base64.b64decode(value)
    return AESGCM(encryption_key()).decrypt(decoded[:12], decoded[12:], None).decode()


def sign_payload(body: bytes) -> str:
    return hmac.new(
        get_settings().webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()


def verify_signature(body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_payload(body), signature)


def delivery_body(event: dict) -> bytes:
    return json.dumps(event, separators=(",", ":"), sort_keys=True).encode()


def fresh_timestamp(timestamp: int, tolerance_seconds: int = 300) -> bool:
    return abs(int(time.time()) - timestamp) <= tolerance_seconds


