from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any


class SecurityError(ValueError):
    pass


class PasswordHasher:
    algorithm = "scrypt"
    salt_length = 16
    key_length = 32

    def hash(self, password: str) -> str:
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        salt = secrets.token_bytes(self.salt_length)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=self.key_length,
        )
        return "$".join(
            (
                self.algorithm,
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(digest).decode("ascii"),
            )
        )

    def verify(self, password: str, encoded: str) -> bool:
        try:
            algorithm, salt_value, digest_value = encoded.split("$", 2)
            if algorithm != self.algorithm:
                return False
            salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
            actual = hashlib.scrypt(
                password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=len(expected)
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, UnicodeError):
            return False


@dataclass(frozen=True)
class AccessToken:
    subject: str
    role: str
    organization_id: str | None
    expires_at: int


class TokenService:
    def __init__(self, secret: str, lifetime_seconds: int = 3600) -> None:
        if len(secret) < 32:
            raise ValueError("AUTH_SECRET_KEY must contain at least 32 characters.")
        self.secret = secret.encode("utf-8")
        self.lifetime_seconds = lifetime_seconds

    def issue(self, subject: str, role: str, organization_id: str | None) -> str:
        now = int(time.time())
        payload = {
            "sub": subject,
            "role": role,
            "org": organization_id,
            "iat": now,
            "exp": now + self.lifetime_seconds,
        }
        encoded_payload = self._encode(payload)
        signature = self._sign(encoded_payload)
        return f"{encoded_payload}.{signature}"

    def verify(self, token: str) -> AccessToken:
        try:
            encoded_payload, signature = token.split(".", 1)
            expected_signature = self._sign(encoded_payload)
            if not hmac.compare_digest(signature, expected_signature):
                raise SecurityError("Invalid access token.")
            payload = self._decode(encoded_payload)
            if int(payload["exp"]) <= int(time.time()):
                raise SecurityError("Access token has expired.")
            return AccessToken(
                subject=str(payload["sub"]),
                role=str(payload["role"]),
                organization_id=payload.get("org"),
                expires_at=int(payload["exp"]),
            )
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise SecurityError("Invalid access token.") from exc

    def _sign(self, encoded_payload: str) -> str:
        digest = hmac.new(self.secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        return self._base64_encode(digest)

    @staticmethod
    def _encode(payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return TokenService._base64_encode(serialized)

    @staticmethod
    def _decode(value: str) -> dict[str, Any]:
        padded_value = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded_value.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict):
            raise SecurityError("Invalid access token.")
        return payload

    @staticmethod
    def _base64_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
