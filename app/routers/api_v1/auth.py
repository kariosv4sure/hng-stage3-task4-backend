from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import unquote

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
# REDIRECT URI HELPER
# ─────────────────────────────
def _get_redirect_uri(request: Request) -> str:
    """Get the callback redirect URI"""
    if PUBLIC_URL:
        return f"{PUBLIC_URL.rstrip('/')}/api/v1/auth/callback"
    
    # Fallback to request base URL
    return f"{str(request.base_url).rstrip('/')}/api/v1/auth/callback"


# ─────────────────────────────
# COOKIE HELPERS
# ─────────────────────────────
def _set_auth_cookies(response, tokens: dict, samesite: str = "lax"):
    """Set authentication cookies"""
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite=samesite,
        max_age=900,  # 15 minutes
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite=samesite,
        max_age=604800,  # 7 days
        path="/",
    )


# ─────────────────────────────
# LOGIN ENDPOINT
# ─────────────────────────────
@router.get("/login")
async def login(request: Request, client: str = Query("web")):
    """Initialize OAuth login flow"""
    if client not in ("cli", "web"):
        raise HTTPException(status_code=400, detail="Invalid client type. Use 'cli' or 'web'")

    # Get the redirect URI
    redirect_uri = _get_redirect_uri(request)
    print(f"Login redirect_uri: {redirect_uri}")
    
    # Build authorization URL
    auth_data = build_authorization_url(redirect_uri, client=client)

    # CLI flow - return JSON with auth URL
    if client == "cli":
        return JSONResponse({
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"],
        })

    # Web flow - redirect to GitHub
    response = RedirectResponse(url=auth_data["auth_url"], status_code=302)
    
    # Store state in cookie for validation
    response.set_cookie(
        key="oauth_state",
        value=auth_data["state"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,  # 10 minutes
        path="/",
    )
    
    return response


# ─────────────────────────────
# CALLBACK ENDPOINT (FIXED)
# ─────────────────────────────
@router.get("/callback")
async def callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Handle OAuth callback from GitHub"""
    print(f"=== CALLBACK RECEIVED ===")
    print(f"Code: {code[:20]}...")
    print(f"Raw State: {state}")
    
    # Get redirect URI (must match what was sent to GitHub)
    redirect_uri = _get_redirect_uri(request)
    print(f"Redirect URI: {redirect_uri}")
    
    # URL decode the state parameter
    decoded_state_param = unquote(state)
    print(f"Decoded State: {decoded_state_param}")
    
    # Extract and validate state
    decoded = extract_state(decoded_state_param)
    if not decoded:
        print("ERROR: Invalid OAuth state")
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    client_type = decoded.get("client", "web")
    print(f"Client type: {client_type}")
    
    # Exchange code for token
    try:
        token_data = await exchange_code_for_token(code, redirect_uri)
        print("Token exchange successful")
    except Exception as e:
        print(f"Token exchange failed: {e}")
        raise
    
    # Get GitHub user info
    try:
        github_user = await get_github_user(token_data["access_token"])
        print("GitHub user fetch successful")
    except Exception as e:
        print(f"GitHub user fetch failed: {e}")
        raise
    
    # Create or get user and generate tokens
    user = AuthService.get_or_create_user(db, github_user)
    tokens = AuthService.create_tokens(db, user)
    print(f"User authenticated: {user.email}")

    # ─────────────────────────────
    # CLI FLOW - Return JSON
    # ─────────────────────────────
    if client_type == "cli":
        print("Returning CLI response")
        return JSONResponse({
            "status": "success",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            }
        })

    # ─────────────────────────────
    # WEB FLOW - Redirect with cookies
    # ─────────────────────────────
    print("Redirecting to dashboard")
    response = RedirectResponse(
        url=f"{WEB_PORTAL_URL}/dashboard.html",
        status_code=302
    )
    
    # Set auth cookies
    _set_auth_cookies(response, tokens, samesite="lax")
    
    # Clean up state cookie
    response.delete_cookie(
        key="oauth_state",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    
    return response


# ─────────────────────────────
# REFRESH TOKEN
# ─────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh access token"""
    tokens = AuthService.refresh_access_token(db, request.refresh_token)

    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return tokens


# ─────────────────────────────
# GET CURRENT USER
# ─────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get current authenticated user"""
    # Check cookie first
    token = request.cookies.get("access_token")
    
    # Fallback to Authorization header
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify token
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Get user
    user = AuthService.get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ─────────────────────────────
# LOGOUT
# ─────────────────────────────
@router.post("/logout")
async def logout():
    """Logout and clear cookies"""
    response = JSONResponse({"status": "success", "message": "Logged out successfully"})
    
    # Clear auth cookies
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key="oauth_state",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    
    return response


# ─────────────────────────────
# TOKEN VERIFICATION (for CLI)
# ─────────────────────────────
@router.get("/verify")
async def verify_token(
    request: Request,
    db: Session = Depends(get_db),
):
    """Verify token validity (useful for CLI tools)"""
    # Check cookie first
    token = request.cookies.get("access_token")
    
    # Fallback to Authorization header
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    
    if not token:
        return JSONResponse({"valid": False, "message": "No token provided"}, status_code=401)

    # Verify token
    payload = verify_access_token(token)
    if not payload:
        return JSONResponse({"valid": False, "message": "Invalid or expired token"}, status_code=401)

    # Get user
    user = AuthService.get_user_by_id(db, payload["sub"])
    if not user:
        return JSONResponse({"valid": False, "message": "User not found"}, status_code=404)

    return JSONResponse({
        "valid": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
        }
    })
