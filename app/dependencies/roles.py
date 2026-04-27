from fastapi import HTTPException, status, Depends
from typing import List

from app.dependencies.auth import get_current_user


def require_roles(allowed_roles: List[str]):
    """Generic role-based access dependency factory."""

    def role_checker(payload: dict = Depends(get_current_user)):
        user_role = payload.get("role")

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "message": "Insufficient permissions",
                },
            )

        return payload

    return role_checker


# Predefined role guards (clean usage in routers)
require_admin = require_roles(["admin"])
require_analyst = require_roles(["admin", "analyst"])

