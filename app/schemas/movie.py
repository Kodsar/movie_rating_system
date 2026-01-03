from pydantic import BaseModel, Field
from typing import List, Optional


class MovieUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    director_id: int = Field(..., ge=1)
    release_year: int = Field(..., ge=1800, le=2100)
    cast: Optional[str] = Field(None, max_length=1000)
    genres: List[int] = Field(default_factory=list)


class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    director_id: int = Field(..., ge=1)
    release_year: int = Field(..., ge=1800, le=2100)
    cast: Optional[str] = Field(None, max_length=1000)
    genres: List[int] = Field(default_factory=list)


class DirectorShort(BaseModel):
    id: int
    name: str


class MovieCreatedResponse(BaseModel):
    id: int
    title: str
    release_year: int
    director: DirectorShort
    genres: List[str]
    cast: Optional[str]
    average_rating: Optional[float]
    ratings_count: int
