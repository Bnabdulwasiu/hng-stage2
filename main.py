from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status, Response
import httpx
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import asyncio
from database import *
from schemas import *
from models import Profile
from utils import get_age_group, profile_to_dict


# Database Setup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError



@asynccontextmanager
async def lifespan(app: FastAPI):
    #Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.genderize = httpx.AsyncClient(base_url="https://api.genderize.io", timeout=10.0)
    app.state.agify = httpx.AsyncClient(base_url="https://api.agify.io", timeout=10.0)
    app.state.nationalize = httpx.AsyncClient(base_url="https://api.nationalize.io", timeout=10.0)
    yield
    await asyncio.gather(

        app.state.genderize.aclose(),
        app.state.agify.aclose(),
        app.state.nationalize.aclose(),

    )


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):

    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": str(exc.detail)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "name is not a string"
        }
    )


# Post function
@app.post("/api/profiles", status_code=201)
async def create_profile(body: CreateProfileRequest):
    name =  body.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "message": "Missing or empty name"
        })

    async with AsyncSessionLocal() as session:
        try:
            gender_res, age_res, nation_res = await asyncio.gather(
                app.state.genderize.get("/", params={"name": name}),
                app.state.agify.get("/", params={"name": name}),
                app.state.nationalize.get("/", params={"name": name}),
            )

        except (httpx.HTTPStatusError, httpx.RequestError):
            raise HTTPException(status_code=502, detail={
                "status": "error",
                "message": "Upstream or server failure"
            })

        gender_data = gender_res.json()
        age_data = age_res.json()
        nation_data = nation_res.json()

        if gender_data.get("gender") is None or gender_data.get("count") == 0:
            raise HTTPException(status_code=502, detail={
                "status": "error",
                "message": "Genderize returned an invalid response"
            })

        if age_data.get("age") is None:
            raise HTTPException(status_code=502, detail={
                "status": "error",
                "message": "Agify returned an invalid response"
            })

        countries = nation_data.get("country", [])
        if not countries:
            raise HTTPException(status_code=502, detail={
                "status": "error",
                "message": "Nationalize returned an invalid response"
            })

        # Pick top country by probability
        top_country = max(countries, key=lambda c: c["probability"]) if countries else None
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        profile = Profile(
            name=name,
            gender=gender_data.get("gender"),
            gender_probability=gender_data.get("probability"),
            sample_size=gender_data.get("count"),
            age=age_data.get("age"),
            age_group=get_age_group(age_data.get("age")),
            country_id=top_country["country_id"] if top_country else None,
            country_probability=top_country["probability"] if top_country else None,
            created_at=created_at,
        )

        session.add(profile)

        try:
            await session.commit()
            await session.refresh(profile)

            return JSONResponse(status_code=201, content={
                "status": "success",
                "data": profile_to_dict(profile)
            })

        except IntegrityError:
            await session.rollback()

            result = await session.execute(
                select(Profile).where(Profile.name == name)
            )
            existing = result.scalar_one()

            return JSONResponse(status_code=200, content={
                "status": "success",
                "message": "Profile already exists",
                "data": profile_to_dict(existing)
            })


@app.get("/api/profiles" , response_model=ProfileListResponse)
async def get_all_profiles(
    gender: Optional[str] = None,
    country_id: Optional[str] = None,
    age_group: Optional[str] = None  # string not int
):
    async with AsyncSessionLocal() as session:
        query = select(Profile)

        # Apply filters if provided
        if gender:
            query = query.where(Profile.gender == gender.lower())
        if country_id:
            query = query.where(Profile.country_id == country_id.upper())
        if age_group:
            query = query.where(Profile.age_group == age_group.lower())

        result = await session.execute(query)
        profiles = result.scalars().all()

        return {
            "status": "success",
            "count": len(profiles),
            "data": [profile_to_dict(p) for p in profiles]
        }


@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Profile).where(Profile.id == profile_id))
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(status_code=404, detail={
                "status": "error",
                "message": "Profile not found"
            })

        return {"status": "success", "data": profile_to_dict(profile)}

    
@app.delete("/api/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: str):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Profile).where(Profile.id == profile_id))
            profile = result.scalar_one_or_none()

            if not profile:
                raise HTTPException(status_code=404, detail={
                    "status": "error",
                    "message": "Profile not found"
                })
            
            await session.delete(profile)
            await session.commit()

            # 4. Return Response(status_code=204) or simply None
            return Response(status_code=status.HTTP_204_NO_CONTENT)