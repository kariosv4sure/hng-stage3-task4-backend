from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.oauth import (
    build_authorization_url,
    exchange_code_for_token,
    get_github_user,
    extract_state,
)
from app.core.security import verify_access_token
from app.services.auth_service import AuthService
from app.schemas.auth import RefreshRequest, TokenResponse, UserResponse
from app.config import PUBLIC_URL

router = APIRouter(prefix="/auth", tags=["Authentication"])

WEB_PORTAL_URL = "https://hng-stage3-task4-web.vercel.app"


# ─────────────────────────────
# REDIRECT URI
# ─────────────────────────────
def _get_redirect_uri(request: Request) -> str:
    if PUBLIC_URL:
        return f"{PUBLIC_URL.rstrip('/')}/api/v1/auth/callback"

    return f"{str(request.base_url).rstrip('/')}/api/v1/auth/callback"


# ─────────────────────────────
# COOKIES
# ─────────────────────────────
def _set_auth_cookies(response, tokens: dict):
    response.set_cookie(
        "access_token",
        tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=900,
    )
    response.set_cookie(
        "refresh_token",
        tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
    )


# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@router.get("/login")
async def login(request: Request, client: str = Query("web")):
    if client not in ("cli", "web"):
        raise HTTPException(status_code=400, detail="Invalid client")

    redirect_uri = _get_redirect_uri(request)
    auth_data = build_authorization_url(redirect_uri, client=client)

    if client == "cli":
        return JSONResponse({
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"],
        })

    response = RedirectResponse(url=auth_data["auth_url"])
    response.set_cookie(
        "oauth_state",
        auth_data["state"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=600,
    )
    return response


# ─────────────────────────────
# CALLBACK (FIXED)
# ─────────────────────────────
@router.get("/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    client: str = Query("web"),
    db: Session = Depends(get_db),
):
    redirect_uri = _get_redirect_uri(request)

    decoded = extract_state(state)

    if not decoded:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    client_type = decoded.get("client", client)

    # ─────────────────────────────
    # GET GITHUB TOKEN
    # ─────────────────────────────
    token_data = await exchange_code_for_token(code, redirect_uri)
    github_user = await get_github_user(token_data["access_token"])

    user = AuthService.get_or_create_user(db, github_user)
    tokens = AuthService.create_tokens(db, user)

    # ─────────────────────────────
    # CLI FLOW
    # ─────────────────────────────
    if client_type == "cli":
        return JSONResponse({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        })

    # ─────────────────────────────
    # WEB FLOW
    # ─────────────────────────────
    response = RedirectResponse(
        url=f"{WEB_PORTAL_URL}/dashboard.html"
    )

    response.set_cookie(
        "access_token",
        tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=900,
    )

    response.set_cookie(
        "refresh_token",
        tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=604800,
    )

    response.delete_cookie("oauth_state")

    return response

"""

@router.get("/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    client: str = Query("web"),
    db: Session = Depends(get_db),
):
    redirect_uri = _get_redirect_uri(request)

    decoded = extract_state(state)

    if not decoded:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    client_type = decoded.get("client", client)

    # ─────────────────────────────
    # CLI FLOW (NO REDIRECTS)
    # ─────────────────────────────
    if client_type == "cli":
        token_data = await exchange_code_for_token(code, redirect_uri)

        github_user = await get_github_user(token_data["access_token"])

        user = AuthService.get_or_create_user(db, github_user)
        tokens = AuthService.create_tokens(db, user)

        return JSONResponse({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        })

    # ─────────────────────────────
    # WEB FLOW
    # ─────────────────────────────
    token_data = await exchange_code_for_token(code, redirect_uri)

    github_user = await get_github_user(token_data["access_token"])

    user = AuthService.get_or_create_user(db, github_user)
    tokens = AuthService.create_tokens(db, user)

    response = RedirectResponse(url=f"{WEB_PORTAL_URL}/dashboard.html")
    _set_auth_cookies(response, tokens)

    response.delete_cookie("oauth_state")
    return response

"""
# ─────────────────────────────
# REFRESH
# ─────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    tokens = AuthService.refresh_access_token(db, request.refresh_token)

    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return tokens


# ─────────────────────────────
# ME
# ─────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")

    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = AuthService.get_user_by_id(db, payload["sub"])

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ─────────────────────────────
# LOGOUT
# ─────────────────────────────
@router.post("/logout")
async def logout():
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
