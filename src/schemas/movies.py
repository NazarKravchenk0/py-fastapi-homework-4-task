from __future__ import annotations

from datetime import date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class CountrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: Optional[str] = None


class GenreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ActorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class LanguageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MovieListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    score: float
    overview: str


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    total_pages: int
    total_items: int
    prev_page: Optional[str] = None
    next_page: Optional[str] = None


class MovieDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float

    country: CountrySchema
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[LanguageSchema]


class MovieCreateSchema(BaseModel):
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float

    country: str = Field(..., description="Country code, e.g. 'US'")
    genres: List[str]
    actors: List[str]
    languages: List[str]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    revenue: Optional[float] = None

    country: Optional[str] = None
    genres: Optional[List[str]] = None
    actors: Optional[List[str]] = None
    languages: Optional[List[str]] = None


class MovieUpdateResponseSchema(BaseModel):
    detail: str
