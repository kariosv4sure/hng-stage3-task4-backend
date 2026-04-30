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
from app.core.security import generate_pkce_pair, generate_state


def _encode(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode(data: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(data.encode()).decode())


# ─────────────────────────────
# AUTH URL BUILDER (FIXED)
# ─────────────────────────────
def build_authorization_url(redirect_uri: str, client: str = "web") -> dict:
    """
    CLI = NO PKCE
    WEB = PKCE enabled
    """

    state_payload = {"state": generate_state(), "client": client}

    code_verifier = None
    pkce_params = ""

    if client == "web":
        code_verifier, code_challenge = generate_pkce_pair()
        state_payload["code_verifier"] = code_verifier

        pkce_params = (
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )

    encoded_state = _encode(state_payload)

    auth_url = (
        f"{GITHUB_AUTH_URL}?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=read:user user:email&"
        f"state={encoded_state}"
        f"{pkce_params}"
    )

    return {
        "auth_url": auth_url,
        "state": encoded_state,
        "code_verifier": code_verifier,
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
async def exchange_code_for_token(
    code: str,
    redirect_uri: str,
    code_verifier: str | None = None
):
    payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    # ONLY include for web flow
    if code_verifier:
        payload["code_verifier"] = code_verifier

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data=payload,
            headers={"Accept": "application/json"},
        )

    data = response.json()

    if response.status_code != 200 or "access_token" not in data:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "OAuth token exchange failed"},
        )

    return data


# ─────────────────────────────
# GITHUB USER FETCH
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

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Failed to fetch GitHub user"},
        )

    return response.json()
