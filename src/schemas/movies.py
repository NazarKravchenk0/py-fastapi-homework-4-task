from typing import List

from pydantic import BaseModel, ConfigDict


class MovieBaseSchema(BaseModel):
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]


class MovieCreateSchema(MovieBaseSchema):
    pass


class MovieListSchema(BaseModel):
    id: int
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]

    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(BaseModel):
    id: int
    title: str
    description: str
    duration: int
    genres: List[str]
    actors: List[str]

    model_config = ConfigDict(from_attributes=True)
