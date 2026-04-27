import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import jwt, JWTError

from app.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(user_id: str, role: str) -> str:
    """Create short-lived JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(expire.timestamp()),
        "type": "access"
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """Verify JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != "access":
            return None

        return payload

    except JWTError:
        return None


def generate_pkce_pair() -> Tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(64)[:128]

    challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge).decode().rstrip("=")

    return code_verifier, code_challenge


def generate_state() -> str:
    """Generate random state for OAuth CSRF protection."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for database storage."""
    return hashlib.sha256(token.encode()).hexdigest()

