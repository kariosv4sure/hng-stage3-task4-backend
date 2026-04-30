from typing import Optional
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_access_token
from app.schemas.profile import (
    ProfileResponse,
    ProfileSummaryResponse,
    PaginatedListResponse,
    GetSuccessResponse,
)
from app.services.profile_service import ProfileService
from app.utils.parser import parse_query

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        return None
    payload = verify_access_token(token)
    return payload if payload else None


def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Not authenticated"})
    return user


def require_admin(request: Request):
    user = require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail={"status": "error", "message": "Admin access required"})
    return user


@router.get("", response_model=PaginatedListResponse)
async def get_all_profiles(
    request: Request,
    gender: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    require_auth(request)

    profiles, total = ProfileService.get_all_filtered(
        db=db, gender=gender, country_id=country_id, age_group=age_group,
        min_age=min_age, max_age=max_age,
        sort_by=sort_by, order=order, page=page, limit=limit,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {
            "self": f"/api/v1/profiles?page={page}&limit={limit}",
            "next": f"/api/v1/profiles?page={page+1}&limit={limit}" if page < total_pages else None,
            "prev": f"/api/v1/profiles?page={page-1}&limit={limit}" if page > 1 else None,
        },
        "data": [ProfileSummaryResponse.model_validate(p) for p in profiles],
    }


@router.get("/search")
async def search_profiles(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    request: Request = None,
    db: Session = Depends(get_db),
):
    require_auth(request)
    filters = parse_query(q)

    profiles, total = ProfileService.get_all_filtered(
        db=db, gender=filters.get("gender"), country_id=filters.get("country_id"),
        age_group=filters.get("age_group"), min_age=filters.get("min_age"),
        max_age=filters.get("max_age"), page=page, limit=limit,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {},
        "data": [ProfileSummaryResponse.model_validate(p) for p in profiles],
    }


@router.get("/{profile_id}", response_model=GetSuccessResponse)
async def get_profile(profile_id: str, request: Request, db: Session = Depends(get_db)):
    require_auth(request)
    profile = ProfileService.get_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Profile not found"})
    return {"status": "success", "data": ProfileResponse.model_validate(profile)}


@router.post("", status_code=201)
async def create_profile(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Invalid JSON"})
    profile, created = ProfileService.create(db, body)
    return {"status": "success", "data": ProfileResponse.model_validate(profile)}


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    profile = ProfileService.get_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Profile not found"})
    ProfileService.delete(db, profile)
    return None
