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


# -------------------------
# ENCODING HELPERS
# -------------------------
def _encode(data: dict) -> str:
    """Encode dictionary to URL-safe base64 string"""
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode(data: str) -> dict:
    """Decode URL-safe base64 string back to dictionary"""
    try:
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += "=" * padding
        return json.loads(base64.urlsafe_b64decode(data.encode()).decode())
    except Exception as e:
        print(f"State decode error: {e}")
        return None


# -------------------------
# BUILD AUTH URL
# -------------------------
def build_authorization_url(redirect_uri: str, client: str = "web") -> dict:
    """Build GitHub OAuth authorization URL"""
    state_payload = {
        "state": generate_state(),
        "client": client,
    }

    encoded_state = _encode(state_payload)

    auth_url = (
        f"{GITHUB_AUTH_URL}"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user user:email"
        f"&state={encoded_state}"
    )

    return {"auth_url": auth_url, "state": encoded_state}


# -------------------------
# STATE PARSE
# -------------------------
def extract_state(state: str) -> dict | None:
    """Extract and decode state parameter"""
    try:
        from urllib.parse import unquote
        
        # First URL decode the state
        decoded_state = unquote(state)
        print(f"Raw state: {state}")
        print(f"Decoded state: {decoded_state}")
        
        # Then decode the base64
        result = _decode(decoded_state)
        print(f"Parsed state: {result}")
        return result
    except Exception as e:
        print(f"State extraction error: {e}")
        return None


# -------------------------
# TOKEN EXCHANGE
# -------------------------
async def exchange_code_for_token(code: str, redirect_uri: str):
    """Exchange authorization code for access token"""
    print(f"Exchanging code with redirect_uri: {redirect_uri}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    data = response.json()
    print(f"Token exchange response status: {response.status_code}")
    print(f"Token exchange response: {data}")

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
    """Fetch GitHub user information"""
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
        print(f"GitHub user fetch failed: {response.status_code}")
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Failed to fetch GitHub user"},
        )

    user_data = response.json()
    print(f"GitHub user fetched: {user_data.get('login')}")
    return user_data
