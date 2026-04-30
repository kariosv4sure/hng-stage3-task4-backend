import json
import base64
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


# ─────────────────────────────
# ENCODING HELPERS
# ─────────────────────────────
def _encode(data: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(data).encode()
    ).decode()


def _decode(data: str) -> dict:
    return json.loads(
        base64.urlsafe_b64decode(data.encode()).decode()
    )


# ─────────────────────────────
# AUTH URL BUILDER (CLEAN)
# ─────────────────────────────
def build_authorization_url(redirect_uri: str, client: str = "web") -> dict:
    """
    GitHub OAuth App flow (NO PKCE).
    Works for both CLI and Web.
    """

    state_payload = {
        "state": generate_state(),
        "client": client,
    }

    encoded_state = _encode(state_payload)

    auth_url = (
        f"{GITHUB_AUTH_URL}?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=read:user user:email&"
        f"state={encoded_state}"
    )

    return {
        "auth_url": auth_url,
        "state": encoded_state,
    }


# ─────────────────────────────
# STATE DECODER (SAFE)
# ─────────────────────────────
def extract_state(state: str) -> dict | None:
    try:
        return _decode(state)
    except Exception:
        return None


# ─────────────────────────────
# TOKEN EXCHANGE (FIXED)
# ─────────────────────────────
async def exchange_code_for_token(code: str):
    """
    GitHub OAuth App exchange.
    NO redirect_uri, NO PKCE.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={
                "Accept": "application/json",
            },
        )

    data = response.json()

    if response.status_code != 200 or "access_token" not in data:
        # 🔥 Debug hook (super important for future issues)
        print("OAUTH ERROR RESPONSE:", data)

        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "OAuth token exchange failed"
            },
        )

    return data


# ─────────────────────────────
# GET GITHUB USER
# ─────────────────────────────
async def get_github_user(access_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

    data = response.json()

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "Failed to fetch GitHub user"
            },
        )

    return data
