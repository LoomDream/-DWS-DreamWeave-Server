from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from itertools import count
from typing import Iterator


def md5_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.md5(data).hexdigest()


def sha256_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def new_nonce() -> str:
    return secrets.token_hex(16)


def make_session_key(server_secret: str, server_nonce: str, client_nonce: str) -> bytes:
    seed = f"{server_secret}:{server_nonce}:{client_nonce}".encode("utf-8")
    return hashlib.sha256(seed).digest()


def server_proof(server_secret: str, server_nonce: str) -> str:
    return md5_hex(f"{server_secret}:{server_nonce}")


def client_proof(server_secret: str, server_nonce: str, client_nonce: str) -> str:
    return md5_hex(f"{server_secret}:{server_nonce}:{client_nonce}")


def developer_proof(developer_secret: str, session_key: bytes, content_md5: str) -> str:
    payload = f"{developer_secret}:{content_md5}:{session_key.hex()}".encode("utf-8")
    return hashlib.md5(payload).hexdigest()


def request_proof(
    server_secret: str,
    session_key: bytes,
    handshake_id: str,
    method: str,
    path: str,
    body_md5: str,
    timestamp: str,
    nonce: str,
) -> str:
    payload = ":".join(
        [
            server_secret,
            session_key.hex(),
            handshake_id,
            method.upper(),
            path,
            body_md5,
            timestamp,
            nonce,
        ]
    )
    return md5_hex(payload)


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def encrypt_json_payload(payload: bytes, session_key: bytes) -> str:
    encrypted = _xor_stream(payload, session_key)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_json_payload(payload: str, session_key: bytes) -> bytes:
    encrypted = base64.b64decode(payload.encode("ascii"))
    return _xor_stream(encrypted, session_key)


def make_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest_hex = stored.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _xor_stream(payload: bytes, session_key: bytes) -> bytes:
    return bytes(byte ^ key_byte for byte, key_byte in zip(payload, _keystream(session_key)))


def _keystream(session_key: bytes) -> Iterator[int]:
    for block_id in count():
        block = hashlib.sha256(session_key + block_id.to_bytes(8, "big")).digest()
        yield from block
