import csv
import io
from sqlalchemy.orm import Session
from app.models.profile import ProfileModel

class ExportService:

    @staticmethod
    def export_profiles_csv(db: Session) -> str:
        """Export all profiles as CSV string."""

        profiles = (
            db.query(ProfileModel)
            .order_by(ProfileModel.created_at.desc())
            .all()
        )

        output = io.StringIO(newline="")
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "id",
            "name",
            "gender",
            "gender_probability",
            "age",
            "age_group",
            "country_id",
            "country_name",
            "country_probability",
            "created_at",
        ])

        # Rows
        for p in profiles:
            writer.writerow([
                p.id,
                p.name,
                p.gender,
                f"{p.gender_probability:.6f}",
                p.age,
                p.age_group,
                p.country_id,
                p.country_name,
                f"{p.country_probability:.6f}",
                p.created_at.isoformat() if p.created_at else "",
            ])

        return output.getvalue()
