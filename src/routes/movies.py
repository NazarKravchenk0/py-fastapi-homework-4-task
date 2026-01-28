from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
    for genre_name in movie.genres:
        genre = await db.scalar(select(GenreModel).where(GenreModel.name == genre_name))
        if not genre:
            genre = GenreModel(name=genre_name)
            db.add(genre)
            await db.flush()
        genres.append(genre)

    actors = []
    for actor_name in movie.actors:
        actor = await db.scalar(select(ActorModel).where(ActorModel.name == actor_name))
        if not actor:
            actor = ActorModel(name=actor_name)
            db.add(actor)
            await db.flush()
        actors.append(actor)

    languages = []
    for lang_name in movie.languages:
        language = await db.scalar(select(LanguageModel).where(LanguageModel.name == lang_name))
        if not language:
            language = LanguageModel(name=lang_name)
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
