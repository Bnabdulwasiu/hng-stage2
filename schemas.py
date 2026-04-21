from pydantic import BaseModel
from typing import Optional, List

class ProfileSchema(BaseModel):
    id: str
    name: str
    gender: Optional[str]
    gender_probability: Optional[float]
    sample_size: Optional[int]
    age: Optional[int]
    age_group: Optional[str]
    country_id: Optional[str]

    class Config:
        from_attributes = True

class ProfileListResponse(BaseModel):
    status: str = "success"
    count: int
    data: List[ProfileSchema]

class CreateProfileRequest(BaseModel):
    name: str