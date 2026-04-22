from fastapi import HTTPException
from models import Profile
import pycountry
from main import *
import json
from sqlalchemy.dialects.postgresql import insert

#Helper functions
def error_response(status_code: int, message: str):
     raise HTTPException(
          status_code=status_code,
          detail={
               "status": "error",
               "message": message
          }
     )


def get_age_group(age: int | None) -> str | None:
    if age is None:
        return None
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


def profile_to_dict(profile: Profile) -> dict:
    return {
        "id": str(profile.id),
        "name": profile.name,
        "gender": profile.gender,
        "gender_probability": profile.gender_probability,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_name": profile.country_name,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def get_country_name(country_id: str) -> str:
    """
    Resolves a 2-letter ISO country code to its full name.
    Example: 'NG' -> 'Nigeria'
    """
    try:
        # country_id should be uppercase for pycountry
        country = pycountry.countries.get(alpha_2=country_id.upper())
        return country.name if country else "Unknown"
    except Exception:
        return "Unknown"
    


async def seed_database():
    async with AsyncSessionLocal() as session:
        with open("seed_profiles.json", "r") as f:
            raw = json.load(f)
            data = raw["profiles"]

            stmt = insert(Profile).values(data)
            stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
            await session.execute(stmt)


        await session.commit()