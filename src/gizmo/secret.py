import base64
import os
from datetime import datetime, timezone
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SERVICE = "gizmo"
_USERNAME = "secret_key"
_INDEX = "_index"
_ROTATED_AT = "_key_rotated_at"

_KEY_BYTES = 32  # AES-256


def _set_rotated_at() -> None:
    keyring.set_password(_SERVICE, _ROTATED_AT, datetime.now(timezone.utc).isoformat())


def key_rotated_at() -> datetime | None:
    stored = keyring.get_password(_SERVICE, _ROTATED_AT)
    return datetime.fromisoformat(stored) if stored else None


def _load_key() -> bytes:
    stored = keyring.get_password(_SERVICE, _USERNAME)
    if stored is None:
        key = os.urandom(_KEY_BYTES)
        keyring.set_password(_SERVICE, _USERNAME, key.hex())
        _set_rotated_at()
        return key
    return bytes.fromhex(stored)


def _new_key() -> bytes:
    return os.urandom(_KEY_BYTES)


def encrypt(value: str) -> str:
    key = _load_key()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, value.encode(), None)
    return base64.urlsafe_b64encode(nonce + ct).decode()


def decrypt(token: str) -> str:
    key = _load_key()
    raw = base64.urlsafe_b64decode(token.encode())
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()


def keyring_list() -> list[str]:
    stored = keyring.get_password(_SERVICE, _INDEX)
    return stored.split(",") if stored else []


def keyring_set(key: str, value: str) -> None:
    keyring.set_password(_SERVICE, key, value)
    keys = keyring_list()
    if key not in keys:
        keys.append(key)
        keyring.set_password(_SERVICE, _INDEX, ",".join(keys))


def keyring_get(key: str) -> str | None:
    return keyring.get_password(_SERVICE, key)


def keyring_delete(key: str) -> None:
    keyring.delete_password(_SERVICE, key)
    keys = keyring_list()
    if key in keys:
        keys.remove(key)
        keyring.set_password(_SERVICE, _INDEX, ",".join(keys))


def keyring_rotate_key(tokens: list[str] | None = None) -> list[str]:
    old_key = _load_key()
    new_key = _new_key()
    reencrypted = []
    for t in (tokens or []):
        raw = base64.urlsafe_b64decode(t.encode())
        plaintext = AESGCM(old_key).decrypt(raw[:12], raw[12:], None)
        nonce = os.urandom(12)
        ct = AESGCM(new_key).encrypt(nonce, plaintext, None)
        reencrypted.append(base64.urlsafe_b64encode(nonce + ct).decode())
    keyring.set_password(_SERVICE, _USERNAME, new_key.hex())
    _set_rotated_at()
    return reencrypted
