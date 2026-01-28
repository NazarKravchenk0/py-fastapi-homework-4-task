from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from database.models.movies import (
    MovieModel,
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel,
)
from schemas.movies import (
    MovieCreateSchema,
    MovieUpdateSchema,
    MovieListResponseSchema,
    MovieResponseSchema,
)

router = APIRouter(prefix="/theater/movies", tags=["movies"])


def _page_url(request: Request, page: int, per_page: int) -> str:
    path = request.url.path
    if path.startswith("/api/v1"):
        path = path[len("/api/v1"):]
    return f"{path}?page={page}&per_page={per_page}"


@router.get("/", response_model=MovieListResponseSchema)
async def get_movies(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    count_stmt = select(MovieModel)
    total_items = len((await db.execute(count_stmt)).scalars().all())

    offset = (page - 1) * per_page

    stmt = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = ceil(total_items / per_page)

    prev_page = _page_url(request, page - 1, per_page) if page > 1 else None
    next_page = _page_url(request, page + 1, per_page) if page < total_pages else None

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post("/", response_model=MovieResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_movie(
    movie: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MovieModel).where(
        MovieModel.name == movie.name,
        MovieModel.date == movie.date,
    )
    result = await db.execute(stmt)
    existing_movie = result.scalar_one_or_none()

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail="Movie with this name and date already exists.",
        )

    country = await db.scalar(select(CountryModel).where(CountryModel.code == movie.country))
    if not country:
        country = CountryModel(code=movie.country)
        db.add(country)
        await db.flush()

    genres = []
    for g in movie.genres:
        genre = await db.scalar(select(GenreModel).where(GenreModel.name == g))
        if not genre:
            genre = GenreModel(name=g)
            db.add(genre)
            await db.flush()
        genres.append(genre)

    actors = []
    for a in movie.actors:
        actor = await db.scalar(select(ActorModel).where(ActorModel.name == a))
        if not actor:
            actor = ActorModel(name=a)
            db.add(actor)
            await db.flush()
        actors.append(actor)

    languages = []
    for l in movie.languages:
        language = await db.scalar(select(LanguageModel).where(LanguageModel.name == l))
        if not language:
            language = LanguageModel(name=l)
            db.add(language)
            await db.flush()
        languages.append(language)

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages,
    )

    db.add(new_movie)
    await db.commit()
    await db.refresh(new_movie)

    return new_movie


@router.get("/{movie_id}/", response_model=MovieResponseSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
    )

    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return movie


@router.patch("/{movie_id}/", response_model=MovieResponseSchema)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    data = movie_data.dict(exclude_unset=True)

    for field, value in data.items():
        setattr(movie, field, value)

    await db.commit()
    await db.refresh(movie)

    return movie


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await db.delete(movie)
    await db.commit()
    return None
