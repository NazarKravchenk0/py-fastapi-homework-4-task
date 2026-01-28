from typing import List

from pydantic import BaseModel, ConfigDict


# ----- Base / Create -----

class MovieBaseSchema(BaseModel):
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]
    languages: List[str] = []


class MovieCreateSchema(MovieBaseSchema):
    pass


# ----- List item -----

class MovieListItemSchema(BaseModel):
    id: int
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]
    languages: List[str] = []

    model_config = ConfigDict(from_attributes=True)


# Some parts of the project/tests may expect a different name for list response schema.
# ✅ Provide aliases to avoid ImportError.
MovieListSchema = MovieListItemSchema
MovieListResponseSchema = MovieListItemSchema


# ----- Detail -----

class MovieDetailSchema(BaseModel):
    id: int
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]
    languages: List[str] = []

    model_config = ConfigDict(from_attributes=True)
