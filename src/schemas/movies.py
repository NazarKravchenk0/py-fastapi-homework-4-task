import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator


class MovieStatusEnum(str, Enum):
    Released = "Released"
    PostProduction = "Post Production"
    InProduction = "In Production"


class MovieBaseSchema(BaseModel):
    name: str
    date: datetime.date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: str = Field(..., min_length=3, max_length=3)
    genres: List[str]
    actors: List[str]
    languages: List[str]

    @validator("country")
    def validate_country(cls, value: str) -> str:
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Country must be ISO 3166-1 alpha-3 code")
        return value.upper()


class MovieCreateSchema(MovieBaseSchema):
    pass


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[datetime.date] = None
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = None
    revenue: Optional[float] = None
    country: Optional[str] = Field(None, min_length=3, max_length=3)
    genres: Optional[List[str]] = None
    actors: Optional[List[str]] = None
    languages: Optional[List[str]] = None

    @validator("country")
    def validate_country(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            if len(value) != 3 or not value.isalpha():
                raise ValueError("Country must be ISO 3166-1 alpha-3 code")
            return value.upper()
        return value


class MovieResponseSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]

    class Config:
        orm_mode = True


class MovieListResponseSchema(BaseModel):
    movies: List[MovieResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int
