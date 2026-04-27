from pydantic import BaseModel, Field
from typing import Optional


class OAuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    redirect_uri: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    github_username: str
    role: str
    email: Optional[str] = None


class LoginURLResponse(BaseModel):
    auth_url: str
    state: str

