import json
import base64
import httpx
from fastapi import HTTPException, status

from app.config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_TOKEN_URL,
    GITHUB_USER_URL,
    GITHUB_AUTH_URL,
)
from app.core.security import generate_pkce_pair, generate_state


# -------------------------
# INTERNAL HELPERS
# -------------------------
def _encode(data: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(data).encode()
    ).decode()


def _decode(data: str) -> dict:
    return json.loads(
        base64.urlsafe_b64decode(data.encode()).decode()
    )


# -------------------------
# OAUTH URL BUILDER
# -------------------------
def build_authorization_url(redirect_uri: str) -> dict:
    """
    PKCE OAuth flow (stateless, production-safe).
    Everything needed for callback is embedded in state.
    """

    code_verifier, code_challenge = generate_pkce_pair()

    state_payload = {
        "state": generate_state(),
        "code_verifier": code_verifier,
    }

    encoded_state = _encode(state_payload)

    auth_url = (
        f"{GITHUB_AUTH_URL}?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=read:user user:email&"
        f"state={encoded_state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )

    return {
        "auth_url": auth_url,
        "state": encoded_state,
    }


def extract_state(state: str) -> dict:
    """Decode OAuth state payload."""
    try:
        return _decode(state)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "Invalid OAuth state"
            },
        )


# -------------------------
# TOKEN EXCHANGE
# -------------------------
async def exchange_code_for_token(
    code: str,
    redirect_uri: str,
    code_verifier: str
) -> dict:
    """Exchange GitHub OAuth code for access token."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )

    data = response.json()

    if response.status_code != 200 or "access_token" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "OAuth token exchange failed",
                "github_response": data,
            },
        )

    return data


# -------------------------
# GITHUB USER FETCH
# -------------------------
async def get_github_user(access_token: str) -> dict:
    """Fetch GitHub user info."""

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
                "message": "Failed to fetch GitHub user",
                "github_response": data,
            },
        )

    return data
