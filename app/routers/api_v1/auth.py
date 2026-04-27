from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.oauth import (
    build_authorization_url,
    exchange_code_for_token,
    get_github_user,
)
from app.core.security import verify_access_token
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth import RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login")
async def login(
    client: str = Query("web"),
    redirect_uri: str = Query(None),
):
    """Start GitHub OAuth flow."""

    if client not in ("cli", "web"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Invalid client type"},
        )

    if not redirect_uri:
        redirect_uri = "http://localhost:8000/api/v1/auth/callback"

    auth_data = build_authorization_url(redirect_uri)

    if client == "cli":
        return JSONResponse(
            content={
                "auth_url": auth_data["auth_url"],
                "state": auth_data["state"],
                "code_verifier": auth_data["code_verifier"],
            }
        )

    response = RedirectResponse(url=auth_data["auth_url"])
    response.set_cookie("oauth_state", auth_data["state"], httponly=True, max_age=600)
    response.set_cookie("code_verifier", auth_data["code_verifier"], httponly=True, max_age=600)
    return response


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    client: str = Query("web"),
    redirect_uri: str = Query("http://localhost:8000/api/v1/auth/callback"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback."""

    code_verifier = request.cookies.get("code_verifier")
    stored_state = request.cookies.get("oauth_state")

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Missing code_verifier"},
        )

    if stored_state != state:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Invalid OAuth state"},
        )

    # Exchange GitHub code for token
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

    response = RedirectResponse(url="/dashboard.html")
    response.set_cookie("access_token", tokens["access_token"], httponly=True, max_age=900)
    response.set_cookie("refresh_token", tokens["refresh_token"], httponly=True, max_age=604800)

    response.delete_cookie("oauth_state")
    response.delete_cookie("code_verifier")

    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token."""

    tokens = AuthService.refresh_access_token(db, request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Invalid refresh token"},
        )

    return tokens


@router.get("/me", response_model=UserResponse)
async def me(request: Request, db: Session = Depends(get_db)):
    """Get current authenticated user."""

    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Not authenticated"},
        )

    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Invalid or expired token"},
        )

    user = db.query(User).filter(User.id == payload["sub"]).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "User not found"},
        )

    return user
