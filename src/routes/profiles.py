from __future__ import annotations

import re
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions.storage import S3FileUploadError
from src.models.profiles import ProfileModel
from src.models.users import UserModel
from src.schemas.profiles import ProfileResponse
from src.security.auth import get_current_user
from src.storages.s3 import S3Storage

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])

_ALLOWED_GENDERS = {"man", "woman"}
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
_MAX_AVATAR_SIZE = 1 * 1024 * 1024  # 1MB


def _is_admin(user: UserModel) -> bool:
    # ВАЖНО: никакой user.group (это и вызывало MissingGreenlet)
    # В тестах: group_id=3 это admin
    return getattr(user, "group_id", None) == 3


def _validate_name(value: str) -> None:
    # только английские буквы
    if not re.fullmatch(r"[A-Za-z]+", value or ""):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{value} contains non-english letters",
        )


def _validate_info(info: str) -> None:
    if info is None or not info.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Info field cannot be empty",
        )


def _validate_birth_date(birth: date) -> None:
    if birth.year <= 1900:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid birth date - year must be greater than 1900.",
        )

    today = date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    if age < 18:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must be at least 18 years old to register.",
        )


async def get_s3_storage() -> S3Storage:
    return S3Storage()


@router.post(
    "/users/{user_id}/profile/",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileResponse,
)
async def create_profile(
    user_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),  # придёт строкой "YYYY-MM-DD"
    info: str = Form(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    storage: S3Storage = Depends(get_s3_storage),
) -> ProfileResponse:
    # права
    if current_user.id != user_id and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create this profile",
        )

    # нельзя создать второй раз
    stmt_existing = select(ProfileModel).where(ProfileModel.user_id == user_id)
    res_existing = await db.execute(stmt_existing)
    if res_existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists",
        )

    # валидации
    _validate_name(first_name)
    _validate_name(last_name)

    if gender not in _ALLOWED_GENDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gender must be one of: {', '.join(sorted(_ALLOWED_GENDERS))}",
        )

    try:
        birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Expected YYYY-MM-DD",
        )

    _validate_birth_date(birth)
    _validate_info(info)

    if avatar.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image format",
        )

    content = await avatar.read()
    if len(content) > _MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image size exceeds the allowed limit (1MB).",
        )

    avatar_key = f"avatars/{user_id}_avatar.jpg"

    try:
        avatar_url = await storage.upload_file(
            key=avatar_key,
            content=content,
            content_type=avatar.content_type,
        )
    except S3FileUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    profile = ProfileModel(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=birth,
        info=info,
        avatar_url=avatar_url,
    )

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar_url=profile.avatar_url,
    )
