from pydantic import BaseModel, Field
from typing import List


class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    director_id: int = Field(..., ge=1)
    release_year: int = Field(..., ge=1800, le=2100)
    cast: str | None = Field(None, max_length=1000)
    genres: List[int] = Field(default_factory=list)


class DirectorOut(BaseModel):
    id: int
    name: str


class MovieOut(BaseModel):
    id: int
    title: str
    release_year: int
    director: DirectorOut
    genres: List[str]
    cast: str | None
    average_rating: float | None
    ratings_count: int
