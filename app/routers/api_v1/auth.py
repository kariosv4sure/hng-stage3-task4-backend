from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
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

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Web portal URL for post-login redirect
WEB_PORTAL_URL = "https://hng-stage3-task4-web.vercel.app"


def _get_redirect_uri(request: Request) -> str:
    """Build absolute redirect URI from PUBLIC_URL env or request."""
    from app.config import PUBLIC_URL

    if PUBLIC_URL:
        return f"{PUBLIC_URL.rstrip('/')}/api/v1/auth/callback"

    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/callback"


def _is_secure(request: Request) -> bool:
    """Check if request is over HTTPS."""
    return request.url.scheme == "https"


def _set_auth_cookies(response, tokens: dict, request: Request):
    """Set HTTP-only auth cookies with production-safe settings."""
    secure = _is_secure(request)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=900,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=604800,
    )


# -------------------------
# LOGIN
# -------------------------
@router.get("/login")
async def login(request: Request, client: str = Query("web")):
    """Start GitHub OAuth login flow."""

    if client not in ("cli", "web"):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Invalid client type"},
        )

    redirect_uri = _get_redirect_uri(request)
    auth_data = build_authorization_url(redirect_uri)

    # CLI → return state (contains PKCE inside)
    if client == "cli":
        return JSONResponse(
            content={
                "auth_url": auth_data["auth_url"],
                "state": auth_data["state"],
            }
        )

    # Web → redirect to GitHub + store state in cookie
    response = RedirectResponse(url=auth_data["auth_url"])
    secure = _is_secure(request)
    response.set_cookie(
        key="oauth_state",
        value=auth_data["state"],
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=600,
    )

    return response


# -------------------------
# CALLBACK
# -------------------------
@router.get("/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    client: str = Query("web"),
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback for CLI and Web clients."""

    redirect_uri = _get_redirect_uri(request)

    # Decode state to extract code_verifier
    decoded = extract_state(state)
    code_verifier = decoded.get("code_verifier")

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Invalid state payload"},
        )

    # Exchange GitHub code for access token
    token_data = await exchange_code_for_token(code, redirect_uri, code_verifier)

    # Fetch GitHub user info
    github_user = await get_github_user(token_data["access_token"])

    # Create or update local user
    user = AuthService.get_or_create_user(db, github_user)

    # Issue JWT tokens
    tokens = AuthService.create_tokens(db, user)

    # CLI → return tokens as JSON
    if client == "cli":
        return JSONResponse(content=tokens)

    # Web → set cookies and redirect to dashboard
    response = RedirectResponse(url=f"{WEB_PORTAL_URL}/dashboard.html")
    _set_auth_cookies(response, tokens, request)

    secure = _is_secure(request)
    response.delete_cookie("oauth_state", secure=secure)

    return response


# -------------------------
# REFRESH TOKEN
# -------------------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh expired access token."""

    tokens = AuthService.refresh_access_token(db, request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Invalid refresh token"},
        )

    return tokens


# -------------------------
# CURRENT USER
# -------------------------
@router.get("/me", response_model=UserResponse)
async def me(request: Request, db: Session = Depends(get_db)):
    """Get current authenticated user from cookie or header."""

    # Try cookie first (web), then header (CLI)
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Not authenticated"},
        )

    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Invalid or expired token"},
        )

    user = AuthService.get_user_by_id(db, payload["sub"])

    if not user:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "User not found"},
        )

    return user

