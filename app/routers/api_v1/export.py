from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.roles import require_admin
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.get(
    "/profiles",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_admin)],
)
async def export_profiles_csv(db: Session = Depends(get_db)):
    """Export all profiles as CSV (admin only)."""
    csv_data = ExportService.export_profiles_csv(db)

    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=profiles.csv"
        },
    )
