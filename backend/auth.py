"""
auth.py — Authentication utilities
===================================
Password hashing and JWT creation/verification.
User / checklist storage lives in db.py (Supabase or in-memory).
"""

import os
import hashlib
import hmac
import base64
import json
import time
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "techrook-super-secret-key-change-in-production")
TOKEN_EXPIRY_HOURS = 24

# ── Password utilities (salted PBKDF2; legacy plain-SHA256 hashes still verify) ──
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("pbkdf2$"):
        _, salt_hex, digest_hex = hashed.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), bytes.fromhex(salt_hex), 200_000)
        return hmac.compare_digest(digest.hex(), digest_hex)
    return hmac.compare_digest(hashlib.sha256(plain.encode()).hexdigest(), hashed)


# ── JWT (manual implementation — no PyJWT dependency needed) ──────────────────
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def create_access_token(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    full_payload = {**payload, "iat": now, "exp": now + TOKEN_EXPIRY_HOURS * 3600}

    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(full_payload).encode())
    signing_input = f"{header_b64}.{payload_b64}"

    signature = hmac.new(
        SECRET_KEY.encode(),
        signing_input.encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{signing_input}.{sig_b64}"


def decode_access_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = _b64url_encode(expected_sig)

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        payload = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None