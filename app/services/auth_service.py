import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.token import RefreshToken
from app.utils.uuid7 import generate_uuid7
from app.core.security import create_access_token, hash_token
from app.config import REFRESH_TOKEN_EXPIRE_DAYS


class AuthService:

    @staticmethod
    def get_or_create_user(db: Session, github_data: dict) -> User:
        """Fetch existing GitHub user or create a new one."""

        github_id = str(github_data["id"])

        user = (
            db.query(User)
            .filter(User.github_id == github_id)
            .first()
        )

        if user:
            user.github_username = github_data["login"]
            user.email = github_data.get("email")
            user.last_login = datetime.now(timezone.utc)

            db.commit()
            db.refresh(user)
            return user

        user = User(
            id=generate_uuid7(),
            github_id=github_id,
            github_username=github_data["login"],
            email=github_data.get("email"),
            role=UserRole.ANALYST,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Fetch user by ID (required for /auth/me)."""

        return (
            db.query(User)
            .filter(User.id == user_id, User.is_active.is_(True))
            .first()
        )

    @staticmethod
    def create_tokens(db: Session, user: User) -> dict:
        """Generate access + refresh token pair."""

        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
        )

        refresh_raw = secrets.token_urlsafe(64)
        refresh_hash = hash_token(refresh_raw)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )

        db.add(
            RefreshToken(
                id=generate_uuid7(),
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=expires_at,
                is_revoked=False,
                created_at=datetime.now(timezone.utc),
            )
        )

        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_raw,
            "token_type": "bearer",
            "expires_in": 60 * 15,  # 15 minutes
        }

    @staticmethod
    def refresh_access_token(db: Session, refresh_raw: str) -> Optional[dict]:
        """Rotate refresh token and issue new access token."""

        token_hash = hash_token(refresh_raw)

        stored = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

        if not stored:
            return None

        # revoke old refresh token (rotation)
        stored.is_revoked = True
        db.flush()

        user = (
            db.query(User)
            .filter(
                User.id == stored.user_id,
                User.is_active.is_(True),
            )
            .first()
        )

        if not user:
            return None

        return AuthService.create_tokens(db, user)

    @staticmethod
    def revoke_user_tokens(db: Session, user_id: str) -> None:
        """Revoke all active refresh tokens for a user."""

        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        ).update(
            {"is_revoked": True},
            synchronize_session=False,
        )

        db.commit()
