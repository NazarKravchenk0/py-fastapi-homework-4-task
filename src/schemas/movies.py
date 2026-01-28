from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---- Base schemas ----

class MovieBaseSchema(BaseModel):
    name: str
    date: str  # если у тебя date = str в API, иначе поменяй на date
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None

    country: Optional[str] = None
    genres: List[str] = []
    actors: List[str] = []
    languages: List[str] = []


class MovieCreateSchema(MovieBaseSchema):
    pass


class MovieUpdateSchema(MovieBaseSchema):
    # обычно update допускает частичные поля, но чтобы не ломать импорты/тесты —
    # оставляем как базу. Если тесты требуют partial update — скажешь, сделаем Optional.
    pass


# ---- List/Response schemas ----

class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: str
    score: Optional[float] = None
    overview: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None

    country: Optional[str] = None
    genres: List[str] = []
    actors: List[str] = []
    languages: List[str] = []

    model_config = ConfigDict(from_attributes=True)


# ✅ Алиасы под все варианты импортов в проекте
MovieListSchema = MovieListItemSchema
MovieListResponseSchema = MovieListItemSchema


class MovieResponseSchema(MovieListItemSchema):
    # чаще всего response == detail
    pass


class MovieDetailSchema(MovieListItemSchema):
    pass
