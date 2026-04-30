import json
import base64
import hashlib
import secrets
import httpx
from fastapi import HTTPException

from app.config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_TOKEN_URL,
    GITHUB_USER_URL,
    GITHUB_AUTH_URL,
)
from app.core.security import generate_state


# -------------------------
# ENCODING HELPERS
# -------------------------
def _encode(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode(data: str) -> dict:
    try:
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += "=" * padding
        return json.loads(base64.urlsafe_b64decode(data.encode()).decode())
    except Exception as e:
        print(f"State decode error: {e}")
        return None


# -------------------------
# PKCE HELPERS
# -------------------------
def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


# -------------------------
# BUILD AUTH URL
# -------------------------
def build_authorization_url(redirect_uri: str, client: str = "web") -> dict:
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    state_payload = {
        "state": generate_state(),
        "client": client,
        "code_verifier": code_verifier,
    }

    encoded_state = _encode(state_payload)

    auth_url = (
        f"{GITHUB_AUTH_URL}"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user user:email"
        f"&state={encoded_state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    return {
        "auth_url": auth_url,
        "state": encoded_state,
        "code_verifier": code_verifier,
    }


# -------------------------
# STATE PARSE
# -------------------------
def extract_state(state: str) -> dict | None:
    try:
        from urllib.parse import unquote
        decoded_state = unquote(state)
        result = _decode(decoded_state)
        return result
    except Exception as e:
        print(f"State extraction error: {e}")
        return None


# -------------------------
# TOKEN EXCHANGE
# -------------------------
async def exchange_code_for_token(code: str, redirect_uri: str, code_verifier: str = None):
    print(f"Exchanging code with redirect_uri: {redirect_uri}")

    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    if code_verifier:
        data["code_verifier"] = code_verifier

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    data = response.json()

    if response.status_code != 200 or "access_token" not in data:
        print("OAUTH ERROR:", data)
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "OAuth token exchange failed",
                "github": data,
            },
        )

    return data


# -------------------------
# GET USER
# -------------------------
async def get_github_user(access_token: str):
    print("Fetching GitHub user info...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Failed to fetch GitHub user"},
        )

    user_data = response.json()
    print(f"GitHub user fetched: {user_data.get('login')}")
    return user_data
