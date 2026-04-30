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


def _add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


def _add_cors_redirect(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


def _get_redirect_uri(request: Request = None) -> str:
    return "https://hng-stage3-task4-backend-production.up.railway.app/api/v1/auth/callback"


def _set_auth_cookies(response, tokens: dict, domain: str = None):
    cookie_settings = {
        "httponly": True,
        "secure": True,
        "samesite": "none",
        "path": "/",
    }
    if domain:
        cookie_settings["domain"] = domain

    response.set_cookie(key="access_token", value=tokens["access_token"], max_age=900, **cookie_settings)
    response.set_cookie(key="refresh_token", value=tokens["refresh_token"], max_age=604800, **cookie_settings)


@router.get("/github")
async def github_auth(request: Request, client: str = Query("web")):
    if client not in ("cli", "web"):
        raise HTTPException(status_code=400, detail="Invalid client type")

    redirect_uri = _get_redirect_uri(request)
    auth_data = build_authorization_url(redirect_uri, client=client)

    if client == "cli":
        return _add_cors(JSONResponse({
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"],
        }))

    response = RedirectResponse(url=auth_data["auth_url"], status_code=302)
    response = _add_cors_redirect(response)
    response.set_cookie(key="oauth_state", value=auth_data["state"], httponly=True, secure=True, samesite="none", max_age=600, path="/")
    return response


@router.get("/login")
async def login(request: Request, client: str = Query("web")):
    if client not in ("cli", "web"):
        raise HTTPException(status_code=400, detail="Invalid client type")

    redirect_uri = _get_redirect_uri(request)
    auth_data = build_authorization_url(redirect_uri, client=client)

    if client == "cli":
        return _add_cors(JSONResponse({
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"],
        }))

    response = RedirectResponse(url=auth_data["auth_url"], status_code=302)
    response = _add_cors_redirect(response)
    response.set_cookie(key="oauth_state", value=auth_data["state"], httponly=True, secure=True, samesite="none", max_age=600, path="/")
    return response


@router.get("/github/callback")
async def github_callback(
    code: str = Query(None),
    state: str = Query(None),
    code_verifier: str = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    return await _handle_callback(code, state, code_verifier, request, db)


@router.get("/callback")
async def callback(
    code: str = Query(None),
    state: str = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    return await _handle_callback(code, state, None, request, db)


async def _handle_callback(code, state, code_verifier, request, db):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    redirect_uri = _get_redirect_uri(request)
    decoded_state_param = unquote(state)
    decoded = extract_state(decoded_state_param)
    if not decoded:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    client_type = decoded.get("client", "web")
    code_verifier = decoded.get("code_verifier")

    try:
        token_data = await exchange_code_for_token(code, redirect_uri, code_verifier)
    except Exception as e:
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")

    try:
        github_user = await get_github_user(token_data["access_token"])
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to fetch GitHub user")

    user = AuthService.get_or_create_user(db, github_user)
    tokens = AuthService.create_tokens(db, user)

    if client_type == "cli":
        return _add_cors(JSONResponse({
            "status": "success",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email or "",
                "github_id": str(getattr(user, 'github_id', '')),
                "github_username": getattr(user, 'github_username', None) or github_user.get('login', ''),
                "username": getattr(user, 'github_username', None) or github_user.get('login', ''),
                "role": getattr(user, 'role', 'admin'),
            }
        }))

    import base64, json
    token_param = base64.urlsafe_b64encode(
        json.dumps({"access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"]}).encode()
    ).decode()

    response = RedirectResponse(url=f"{WEB_PORTAL_URL}/dashboard.html?token={token_param}", status_code=302)
    response = _add_cors_redirect(response)
    _set_auth_cookies(response, tokens)
    response.delete_cookie(key="oauth_state", path="/", secure=True, httponly=True, samesite="none")
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    if not request.refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh token")

    tokens = AuthService.refresh_access_token(db, request.refresh_token)
    if not tokens:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Invalid or expired refresh token"})

    return _add_cors(JSONResponse({
        "status": "success",
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }))


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
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = AuthService.get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _add_cors(JSONResponse({
        "id": str(user.id),
        "email": user.email or "",
        "github_id": str(getattr(user, 'github_id', '')),
        "github_username": getattr(user, 'github_username', None) or "",
        "username": getattr(user, 'github_username', None) or "",
        "role": getattr(user, 'role', 'admin') or "admin",
    }))


@router.post("/logout")
async def logout():
    response = JSONResponse({"status": "success", "message": "Logged out successfully"})
    cookie_settings = {"path": "/", "secure": True, "httponly": True, "samesite": "none"}
    response.delete_cookie(key="access_token", **cookie_settings)
    response.delete_cookie(key="refresh_token", **cookie_settings)
    response.delete_cookie(key="oauth_state", **cookie_settings)
    return _add_cors(response)


@router.get("/logout")
async def logout_get():
    raise HTTPException(status_code=405, detail={"status": "error", "message": "Method not allowed. Use POST."})

