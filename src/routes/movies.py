from __future__ import annotations

from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import get_db
from database.models.movies import (
    ActorModel,
    CountryModel,
    GenreModel,
    LanguageModel,
    MovieModel,
)
from schemas.movies import (
    MovieCreateSchema,
    MovieDetailSchema,
    MovieListResponseSchema,
    MovieUpdateResponseSchema,
    MovieUpdateSchema,
)

router = APIRouter(prefix="/movies", tags=["Movies"])

_BASE_PATH = "/theater/movies/"
_MAX_PER_PAGE = 20


def _build_page_links(*, page: int, per_page: int, total_pages: int) -> tuple[Optional[str], Optional[str]]:
    prev_page = (
        f"{_BASE_PATH}?page={page - 1}&per_page={per_page}" if page > 1 and total_pages > 0 else None
    )
    next_page = (
        f"{_BASE_PATH}?page={page + 1}&per_page={per_page}" if page < total_pages else None
    )
    return prev_page, next_page


async def _get_or_create_country(db: AsyncSession, country_code: str) -> CountryModel:
    country = await db.scalar(select(CountryModel).where(CountryModel.code == country_code))
    if country:
        return country
    country = CountryModel(code=country_code)
    db.add(country)
    await db.flush()
    return country


async def _get_or_create_genre(db: AsyncSession, name: str) -> GenreModel:
    genre = await db.scalar(select(GenreModel).where(GenreModel.name == name))
    if genre:
        return genre
    genre = GenreModel(name=name)
    db.add(genre)
    await db.flush()
    return genre


async def _get_or_create_actor(db: AsyncSession, name: str) -> ActorModel:
    actor = await db.scalar(select(ActorModel).where(ActorModel.name == name))
    if actor:
        return actor
    actor = ActorModel(name=name)
    db.add(actor)
    await db.flush()
    return actor


async def _get_or_create_language(db: AsyncSession, name: str) -> LanguageModel:
    language = await db.scalar(select(LanguageModel).where(LanguageModel.name == name))
    if language:
        return language
    language = LanguageModel(name=name)
    db.add(language)
    await db.flush()
    return language


@router.get("/", response_model=MovieListResponseSchema)
async def get_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=_MAX_PER_PAGE),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    total_items = await db.scalar(select(func.count(MovieModel.id)))
    total_items = int(total_items or 0)

    if total_items == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No movies found.")

    total_pages = ceil(total_items / per_page)
    if page > total_pages:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found.")

    offset = (page - 1) * per_page
    stmt = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    movies = (await db.execute(stmt)).scalars().all()

    prev_page, next_page = _build_page_links(page=page, per_page=per_page, total_pages=total_pages)

    return MovieListResponseSchema(
        movies=movies,
        total_pages=total_pages,
        total_items=total_items,
        prev_page=prev_page,
        next_page=next_page,
    )


@router.get("/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie_by_id(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
    )
    movie = (await db.execute(stmt)).scalars().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    return MovieDetailSchema.model_validate(movie)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MovieDetailSchema)
async def create_movie(
    movie_data: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    existing = await db.scalar(
        select(MovieModel).where(MovieModel.name == movie_data.name, MovieModel.date == movie_data.date)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie with the same name and date already exists.",
        )

    country = await _get_or_create_country(db, movie_data.country)
    genres = [await _get_or_create_genre(db, name) for name in movie_data.genres]
    actors = [await _get_or_create_actor(db, name) for name in movie_data.actors]
    languages = [await _get_or_create_language(db, name) for name in movie_data.languages]

    movie = MovieModel(
        name=movie_data.name,
        date=movie_data.date,
        score=movie_data.score,
        overview=movie_data.overview,
        status=movie_data.status,
        budget=movie_data.budget,
        revenue=movie_data.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages,
    )

    db.add(movie)
    await db.commit()

    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie.id)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
    )
    created_movie = (await db.execute(stmt)).scalars().first()
    return MovieDetailSchema.model_validate(created_movie)


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    movie = await db.scalar(select(MovieModel).where(MovieModel.id == movie_id))
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    await db.delete(movie)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{movie_id}/", response_model=MovieUpdateResponseSchema)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
) -> MovieUpdateResponseSchema:
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
    )
    movie = (await db.execute(stmt)).scalars().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )

    if movie_data.name is not None:
        movie.name = movie_data.name
    if movie_data.date is not None:
        movie.date = movie_data.date
    if movie_data.score is not None:
        movie.score = movie_data.score
    if movie_data.overview is not None:
        movie.overview = movie_data.overview
    if movie_data.status is not None:
        movie.status = movie_data.status
    if movie_data.budget is not None:
        movie.budget = movie_data.budget
    if movie_data.revenue is not None:
        movie.revenue = movie_data.revenue
    if movie_data.country is not None:
        movie.country = await _get_or_create_country(db, movie_data.country)

    if movie_data.genres is not None:
        movie.genres = [await _get_or_create_genre(db, name) for name in movie_data.genres]
    if movie_data.actors is not None:
        movie.actors = [await _get_or_create_actor(db, name) for name in movie_data.actors]
    if movie_data.languages is not None:
        movie.languages = [await _get_or_create_language(db, name) for name in movie_data.languages]

    await db.commit()
    return MovieUpdateResponseSchema(detail="Movie updated successfully.")
