from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.oauth import (
    build_authorization_url,
    exchange_code_for_token,
    get_github_user,
    extract_state,   # ✅ FIXED IMPORT
)
from app.core.security import verify_access_token
from app.services.auth_service import AuthService
from app.schemas.auth import RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_redirect_uri(request: Request) -> str:
    from app.config import PUBLIC_URL

    if PUBLIC_URL:
        return f"{PUBLIC_URL.rstrip('/')}/api/v1/auth/callback"

    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/callback"


def _is_secure(request: Request) -> bool:
    return request.url.scheme == "https"


def _set_auth_cookies(response, tokens: dict, request: Request):
    secure = _is_secure(request)

    response.set_cookie(
        "access_token",
        tokens["access_token"],
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=900,
    )

    response.set_cookie(
        "refresh_token",
        tokens["refresh_token"],
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

    if client not in ("cli", "web"):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Invalid client type"},
        )

    redirect_uri = _get_redirect_uri(request)
    auth_data = build_authorization_url(redirect_uri)

    # CLI → just return state (contains PKCE inside)
    if client == "cli":
        return JSONResponse(
            content={
                "auth_url": auth_data["auth_url"],
                "state": auth_data["state"],
            }
        )

    # Web → redirect + store state
    response = RedirectResponse(url=auth_data["auth_url"])

    secure = _is_secure(request)
    response.set_cookie(
        "oauth_state",
        auth_data["state"],
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

    redirect_uri = _get_redirect_uri(request)

    # 🔥 FIX: decode state properly
    decoded = extract_state(state)
    code_verifier = decoded.get("code_verifier")

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Invalid state payload"},
        )

    token_data = await exchange_code_for_token(
        code,
        redirect_uri,
        code_verifier
    )

    github_user = await get_github_user(token_data["access_token"])

    user = AuthService.get_or_create_user(db, github_user)
    tokens = AuthService.create_tokens(db, user)

    if client == "cli":
        return JSONResponse(content=tokens)

    response = RedirectResponse(url="/docs")
    _set_auth_cookies(response, tokens, request)

    return response


# -------------------------
# REFRESH
# -------------------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):

    tokens = AuthService.refresh_access_token(db, request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Invalid refresh token"},
        )

    return tokens


# -------------------------
# ME
# -------------------------
@router.get("/me", response_model=UserResponse)
async def me(request: Request, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(401, "Not authenticated")

    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(401, "Invalid token")

    user = AuthService.get_user_by_id(db, payload["sub"])

    if not user:
        raise HTTPException(404, "User not found")

    return user
