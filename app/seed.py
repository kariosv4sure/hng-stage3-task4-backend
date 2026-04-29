import json
import sys
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, init_db
from app.models.profile import ProfileModel
from app.utils.uuid7 import generate_uuid7
from app.services.profile_service import get_age_group


def seed_profiles(json_file: str = "app/data/profiles_2026.json"):
    """Seed database with profiles from JSON file."""

    init_db()
    db = SessionLocal()

    try:
        print(f"📂 Loading data from {json_file}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        profiles = data.get("profiles", [])

        if not profiles:
            print("⚠️ No profiles found in JSON")
            return

        print(f"📊 Found {len(profiles)} profiles")

        existing_names = {
            name for (name,) in db.query(ProfileModel.name).all()
        }

        inserted = 0
        skipped = 0

        for item in profiles:
            try:
                name = item["name"].strip().lower()

                if name in existing_names:
                    skipped += 1
                    continue

                profile = ProfileModel(
                    id=generate_uuid7(),
                    name=name,
                    gender=item["gender"],
                    gender_probability=item["gender_probability"],
                    age=item["age"],
                    age_group=get_age_group(item["age"]),
                    country_id=item["country_id"],
                    country_name=item["country_name"],
                    country_probability=item["country_probability"],
                )

                db.add(profile)
                existing_names.add(name)
                inserted += 1

            except IntegrityError:
                db.rollback()
                skipped += 1

        db.commit()

        print("\n======================")
        print("✅ SEED COMPLETE")
        print(f"Inserted: {inserted}")
        print(f"Skipped: {skipped}")
        print(f"Total DB: {db.query(ProfileModel).count()}")
        print("======================")

    except FileNotFoundError:
        print("❌ JSON file not found")
        sys.exit(1)

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    seed_profiles()
