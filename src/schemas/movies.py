from typing import List

from pydantic import BaseModel, ConfigDict


class MovieBaseSchema(BaseModel):
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]
    languages: List[str] = []  # если у тебя есть языки в модели/эндпоинтах


class MovieCreateSchema(MovieBaseSchema):
    pass


class MovieListSchema(BaseModel):
    id: int
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]
    languages: List[str] = []

    model_config = ConfigDict(from_attributes=True)


# ✅ АЛИАС, чтобы не падали импорты
MovieListResponseSchema = MovieListSchema


class MovieDetailSchema(BaseModel):
    id: int
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]
    languages: List[str] = []

    model_config = ConfigDict(from_attributes=True)
