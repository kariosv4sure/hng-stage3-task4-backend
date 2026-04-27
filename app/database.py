from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

# -------------------
# SQLite compatibility fix
# -------------------
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

# -------------------
# Engine
# -------------------
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# -------------------
# Session factory
# -------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# -------------------
# Base model
# -------------------
Base = declarative_base()


# -------------------
# DB initializer
# -------------------
def init_db():
    """Create all tables in database."""
    try:
        # Ensure models are registered
        from app.models import profile, user, token  # noqa
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise RuntimeError(f"Database initialization failed: {str(e)}")


# -------------------
# DB dependency
# -------------------
def get_db():
    """Yield DB session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
