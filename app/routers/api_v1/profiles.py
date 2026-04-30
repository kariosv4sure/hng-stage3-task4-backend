from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.roles import require_analyst
from app.core.security import verify_access_token
from app.schemas.profile import (
    ProfileResponse,
    ProfileSummaryResponse,
    PaginatedListResponse,
    GetSuccessResponse,
    ErrorResponse,
)
from app.services.profile_service import ProfileService
from app.utils.parser import parse_query

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_current_user_role(request: Request, db: Session) -> dict:
    """Extract user info from token for role checks"""
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        return None
    
    payload = verify_access_token(token)
    return payload if payload else None


def handle_value_error(e: Exception):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"status": "error", "message": str(e)},
    )


@router.get("", response_model=PaginatedListResponse)
async def get_all_profiles(
    request: Request,
    gender: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    min_gender_probability: Optional[float] = Query(None, ge=0, le=1),
    min_country_probability: Optional[float] = Query(None, ge=0, le=1),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get profiles with filtering + pagination."""
    try:
        profiles, total = ProfileService.get_all_filtered(
            db=db,
            gender=gender,
            country_id=country_id,
            age_group=age_group,
            min_age=min_age,
            max_age=max_age,
            min_gender_probability=min_gender_probability,
            min_country_probability=min_country_probability,
            sort_by=sort_by,
            order=order,
            page=page,
            limit=limit,
        )
    except ValueError as e:
        handle_value_error(e)

    return PaginatedListResponse(
        status="success",
        page=page,
        limit=limit,
        total=total,
        data=[ProfileSummaryResponse.model_validate(p) for p in profiles],
    )


@router.get("/search", response_model=PaginatedListResponse)
async def search_profiles(
    q: str = Query(..., min_length=1),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Natural language search."""
    try:
        filters = parse_query(q)
    except ValueError as e:
        handle_value_error(e)

    try:
        profiles, total = ProfileService.get_all_filtered(
            db=db,
            gender=filters.get("gender"),
            country_id=filters.get("country_id"),
            age_group=filters.get("age_group"),
            min_age=filters.get("min_age"),
            max_age=filters.get("max_age"),
            sort_by=sort_by or filters.get("sort_by"),
            order=order or filters.get("order", "asc"),
            page=page,
            limit=limit,
        )
    except ValueError as e:
        handle_value_error(e)

    return PaginatedListResponse(
        status="success",
        page=page,
        limit=limit,
        total=total,
        data=[ProfileSummaryResponse.model_validate(p) for p in profiles],
    )


@router.get("/{profile_id}", response_model=GetSuccessResponse)
async def get_profile(
    profile_id: str,
    db: Session = Depends(get_db),
):
    """Get single profile by ID."""
    profile = ProfileService.get_by_id(db, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "Profile not found"},
        )

    return GetSuccessResponse(
        status="success",
        data=ProfileResponse.model_validate(profile),
    )


@router.post("", response_model=GetSuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new profile (admin only)."""
    user = get_current_user_role(request, db)
    if not user:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Not authenticated"})
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail={"status": "error", "message": "Only admins can create profiles"})

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Invalid JSON body"})

    try:
        profile, created = ProfileService.create(db, body)
    except ValueError as e:
        handle_value_error(e)

    return GetSuccessResponse(
        status="success",
        data=ProfileResponse.model_validate(profile),
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete profile by ID (admin only)."""
    user = get_current_user_role(request, db)
    if not user:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Not authenticated"})
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail={"status": "error", "message": "Only admins can delete profiles"})

    profile = ProfileService.get_by_id(db, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "Profile not found"},
        )

    ProfileService.delete(db, profile)
    return None
