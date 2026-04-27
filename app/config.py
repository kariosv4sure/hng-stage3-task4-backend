import os
from dotenv import load_dotenv

load_dotenv()

# -------------------
# Database
# -------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./profiles.db")

# -------------------
# GitHub OAuth
# -------------------
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    raise RuntimeError(
        "GitHub OAuth not configured. Missing GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET."
    )

# -------------------
# JWT Settings
# -------------------
JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET or JWT_SECRET.strip() == "":
    raise RuntimeError(
        "JWT_SECRET is missing or invalid. Set a strong secret in environment variables."
    )

JWT_ALGORITHM = "HS256"

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
except ValueError:
    raise ValueError(
        "ACCESS_TOKEN_EXPIRE_MINUTES and REFRESH_TOKEN_EXPIRE_DAYS must be integers."
    )

# -------------------
# Rate Limiting
# -------------------
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")

# Public URL (for OAuth redirects behind proxies)
PUBLIC_URL = os.getenv("PUBLIC_URL", "")
