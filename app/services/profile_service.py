from typing import Dict, Tuple, Optional, List
from sqlalchemy import desc, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.models.profile import ProfileModel
from app.utils.uuid7 import generate_uuid7


# -------------------
# Country mapping
# -------------------
COUNTRY_MAP = {
    "AO": "Angola", "BJ": "Benin", "BW": "Botswana", "BF": "Burkina Faso",
    "BI": "Burundi", "CM": "Cameroon", "CV": "Cape Verde", "CF": "Central African Republic",
    "TD": "Chad", "KM": "Comoros", "CG": "Republic of the Congo", "CD": "DR Congo",
    "CI": "Côte d'Ivoire", "DJ": "Djibouti", "EG": "Egypt", "GQ": "Equatorial Guinea",
    "ER": "Eritrea", "SZ": "Eswatini", "ET": "Ethiopia", "GA": "Gabon",
    "GM": "Gambia", "GH": "Ghana", "GN": "Guinea", "GW": "Guinea-Bissau",
    "KE": "Kenya", "LS": "Lesotho", "LR": "Liberia", "LY": "Libya",
    "MG": "Madagascar", "MW": "Malawi", "ML": "Mali", "MR": "Mauritania",
    "MU": "Mauritius", "MA": "Morocco", "MZ": "Mozambique", "NA": "Namibia",
    "NE": "Niger", "NG": "Nigeria", "RW": "Rwanda", "SN": "Senegal",
    "ZA": "South Africa", "SS": "South Sudan", "SD": "Sudan", "TZ": "Tanzania",
    "UG": "Uganda", "ZM": "Zambia", "ZW": "Zimbabwe",
    "US": "United States", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "CA": "Canada", "AU": "Australia",
    "JP": "Japan", "CN": "China", "IN": "India", "BR": "Brazil"
}


# -------------------
# Age grouping
# -------------------
def get_age_group(age: int) -> str:
    if 0 <= age <= 12:
        return "child"
    if 13 <= age <= 19:
        return "teenager"
    if 20 <= age <= 59:
        return "adult"
    return "senior"


# -------------------
# Service Layer
# -------------------
class ProfileService:

    ALLOWED_SORT_FIELDS = {"age", "created_at", "gender_probability"}

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[ProfileModel]:
        return (
            db.query(ProfileModel)
            .filter(ProfileModel.name == name.strip().lower())
            .first()
        )

    @staticmethod
    def get_by_id(db: Session, profile_id: str) -> Optional[ProfileModel]:
        return (
            db.query(ProfileModel)
            .filter(ProfileModel.id == profile_id)
            .first()
        )

    @staticmethod
    def get_all_filtered(
        db: Session,
        gender: Optional[str] = None,
        country_id: Optional[str] = None,
        age_group: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        min_gender_probability: Optional[float] = None,
        min_country_probability: Optional[float] = None,
        sort_by: Optional[str] = None,
        order: str = "asc",
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[ProfileModel], int]:

        if page < 1 or limit < 1 or limit > 50:
            raise ValueError("Invalid query parameters")

        if order not in ("asc", "desc"):
            raise ValueError("Invalid query parameters")

        if sort_by and sort_by not in ProfileService.ALLOWED_SORT_FIELDS:
            raise ValueError("Invalid query parameters")

        query = db.query(ProfileModel)

        if gender:
            query = query.filter(ProfileModel.gender == gender.lower())

        if country_id:
            query = query.filter(ProfileModel.country_id == country_id.upper())

        if age_group:
            query = query.filter(ProfileModel.age_group == age_group.lower())

        if min_age is not None:
            query = query.filter(ProfileModel.age >= min_age)

        if max_age is not None:
            query = query.filter(ProfileModel.age <= max_age)

        if min_gender_probability is not None:
            query = query.filter(
                ProfileModel.gender_probability >= min_gender_probability
            )

        if min_country_probability is not None:
            query = query.filter(
                ProfileModel.country_probability >= min_country_probability
            )

        total = query.count()

        if sort_by:
            col = getattr(ProfileModel, sort_by)
            query = query.order_by(desc(col) if order == "desc" else asc(col))
        else:
            query = query.order_by(desc(ProfileModel.created_at))

        return query.offset((page - 1) * limit).limit(limit).all(), total

    @staticmethod
    def create(db: Session, profile_data: Dict) -> Tuple[ProfileModel, bool]:
        """
        Returns:
            (profile, is_existing)
        """

        name = profile_data["name"].strip().lower()
        age = profile_data["age"]
        country_id = profile_data["country_id"].upper()

        # check first before insert (reduces exceptions)
        existing = ProfileService.get_by_name(db, name)
        if existing:
            return existing, True

        country_name = COUNTRY_MAP.get(country_id, "Unknown")

        profile = ProfileModel(
            id=generate_uuid7(),
            name=name,
            gender=profile_data["gender"].lower(),
            gender_probability=profile_data["gender_probability"],
            age=age,
            age_group=get_age_group(age),
            country_id=country_id,
            country_name=country_name,
            country_probability=profile_data["country_probability"],
        )

        try:
            db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile, False

        except IntegrityError:
            db.rollback()
            existing = ProfileService.get_by_name(db, name)
            return existing, True

    @staticmethod
    def delete(db: Session, profile: ProfileModel) -> None:
        db.delete(profile)
        db.commit()
