from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator


# -------------------------
# Request
# -------------------------
class CreateProfileRequest(BaseModel):
    name: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip().lower()


# -------------------------
# Response Models
# -------------------------
class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: datetime


class ProfileSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: datetime


# -------------------------
# Paginated Response
# -------------------------
class PaginatedListResponse(BaseModel):
    status: str = "success"
    page: int
    limit: int
    total: int
    data: List[ProfileSummaryResponse]


# -------------------------
# Action Responses
# -------------------------
class CreateSuccessResponse(BaseModel):
    status: str = "success"
    data: ProfileResponse
    message: Optional[str] = None


class ExistingSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    data: ProfileResponse


class GetSuccessResponse(BaseModel):
    status: str = "success"
    data: ProfileResponse


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str

