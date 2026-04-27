Insighta Labs+ (Stage 3 Backend)

A FastAPI backend for secure profile intelligence, authentication, and advanced querying. Built on top of the Stage 2 system with added identity, roles, and production-ready structure.


---

🚀 Overview

Insighta Labs+ upgrades the Stage 2 engine into a real-world backend platform with:

GitHub OAuth (PKCE-based)

JWT access + refresh tokens

Role-based access control (admin / analyst)

Profile filtering + natural language search

CSV export (admin-only)

Rate limiting + request logging

Dual interface support (CLI + Web portal architecture)


Stage 2 functionality is fully preserved.


---

🧠 Tech Stack

FastAPI

SQLAlchemy

SQLite / PostgreSQL

Pydantic v2

httpx

python-jose (JWT)

slowapi (rate limiting)



---

📁 Project Structure

app/
 ├── core/               # Auth, OAuth, security
 ├── models/            # Database models
 ├── schemas/           # API schemas
 ├── services/          # Business logic layer
 ├── routers/           # API routes (v1)
 ├── middleware/        # Logging, rate limiting
 ├── dependencies/      # Auth + role guards
 ├── utils/             # UUID + parser utilities
 ├── config.py
 ├── database.py
 └── main.py


---

🔐 System Architecture

The system is split into clear layers:

Routers → Handle HTTP requests

Services → Business logic (profiles, auth, export)

Models → Database schema (SQLAlchemy)

Schemas → Request/response validation

Core → Security + OAuth logic

Dependencies → Auth guards (JWT + roles)



---

🔑 Authentication Flow

1. User initiates login via /api/v1/auth/login


2. Redirected to GitHub OAuth (PKCE secured)


3. GitHub returns authorization code


4. Backend exchanges code for access token


5. GitHub user data is fetched


6. Local user is created or updated


7. System issues:

JWT Access Token (short-lived)

Refresh Token (stored hashed in DB)



8. Tokens used for protected routes




---

🛡️ Token Handling

Access tokens: short-lived JWT (15 min default)

Refresh tokens: stored hashed in DB

Refresh rotation: old token invalidated on use

Tokens can be passed via:

Authorization header (CLI)

HTTP-only cookies (Web)




---

👥 Role Enforcement

Two roles exist:

admin → full access + CSV export

analyst → profile access only


Enforcement is handled via dependency guards:

require_admin

require_analyst


Every protected endpoint validates role before execution.


---

📊 Profile System (Stage 2 Core)

Still fully supported:

External API aggregation (gender, age, nationality)

UUID v7 identifiers

Filtering by:

gender

country

age group

probability thresholds


Pagination + sorting



---

🧠 Natural Language Parsing

Users can query profiles using natural language:

Examples:

"young males"

"females above 30"

"people from nigeria"

"adult males from kenya"


The parser converts queries into structured filters used by the database layer.


---

🔗 API Endpoints

Auth

GET  /api/v1/auth/login
GET  /api/v1/auth/callback
POST /api/v1/auth/refresh
GET  /api/v1/auth/me

Profiles

GET    /api/v1/profiles
GET    /api/v1/profiles/search
GET    /api/v1/profiles/{id}
DELETE /api/v1/profiles/{id}

Export

GET /api/v1/export/profiles


---

⚙️ Setup

Clone Repo

git clone https://github.com/kariosv4sure/hng-stage3-task4-backend.git
Install dependencies

pip install -r requirements.txt

Environment variables

DATABASE_URL=sqlite:///./profiles.db
JWT_SECRET=your_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_AUTH_URL=https://github.com/login/oauth/authorize
GITHUB_TOKEN_URL=https://github.com/login/oauth/access_token
GITHUB_USER_URL=https://api.github.com/user


---

▶️ Run Locally

uvicorn app.main:app --reload

Docs:

http://localhost:8000/docs


---

🚀 Deployment

Recommended (Railway / similar):

1. Push repo to GitHub


2. Connect to Railway


3. Add environment variables


4. Deploy



Start command:

uvicorn app.main:app --host 0.0.0.0 --port $PORT


---

🧪 Testing Strategy

After deployment:

/health → verify server status

/api/v1/auth/login → OAuth flow

/api/v1/profiles → core dataset

/api/v1/profiles/search?q=adult males

/api/v1/export/profiles (admin only)



---

⚠️ Notes

Stage 2 logic must not break

OAuth requires correct env configuration

Role-based access enforced on every protected route

UUID v7 used for all primary keys



---

💀 Reality Check

If your env vars or OAuth setup is wrong, deployment will fail immediately. No backend will "auto-fix" misconfiguration.


---

Built for HNG Stage 3 🚀
