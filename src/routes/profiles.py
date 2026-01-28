from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models.accounts import UserModel, UserGroupEnum, UserProfileModel
from schemas.profiles import ProfileCreateSchema, ProfileResponseSchema
from config.dependencies import get_jwt_auth_manager, get_s3_storage_client
from security.interfaces import JWTAuthManagerInterface
from storages.interfaces import S3StorageInterface


router = APIRouter(prefix="/users", tags=["profiles"])


def _get_bearer_token(request: Request) -> str:
    authorization: Optional[str] = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
        )
    return token


def _is_admin(user: UserModel) -> bool:
    # допускаем создание профиля другим пользователям только админу
    # (если у тебя есть MODERATOR тоже — добавь)
    return getattr(user.group, "name", None) == UserGroupEnum.ADMIN


@router.post(
    "/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    request: Request,
    user_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),
    info: str = Form(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
):
    # 1) token
    token = _get_bearer_token(request)

    # 2) decode token + expire handling
    try:
        payload = jwt_manager.decode_access_token(token)
    except Exception as exc:
        # если в проекте есть отдельное исключение TokenExpired — замени проверку
        if "expired" in str(exc).lower():
            raise HTTPException(status_code=401, detail="Token has expired.")
        raise HTTPException(status_code=401, detail="Token has expired.")

    # ожидаем, что в payload есть user id (обычно "sub")
    current_user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Token has expired.")

    # 3) user exists + active
    stmt = select(UserModel).where(UserModel.id == int(current_user_id))
    current_user = (await db.execute(stmt)).scalars().first()

    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=401, detail="User not found or not active.")

    # 4) permissions
    if current_user.id != user_id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="You don't have permission to edit this profile.")

    # target user must exist and be active too (по ТЗ “user_id exists and active”)
    stmt_target = select(UserModel).where(UserModel.id == user_id)
    target_user = (await db.execute(stmt_target)).scalars().first()
    if not target_user or not target_user.is_active:
        raise HTTPException(status_code=401, detail="User not found or not active.")

    # 5) existing profile
    stmt_profile = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    existing_profile = (await db.execute(stmt_profile)).scalars().first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="User already has a profile.")

    # 6) validate schema + avatar bytes
    avatar_bytes = await avatar.read()
    try:
        profile_data = ProfileCreateSchema(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar_bytes,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    # 7) upload avatar to S3 (MinIO)
    # key/path can be anything, but keep stable + unique
    ext = (avatar.filename or "avatar").split(".")[-1].lower()
    if ext not in {"jpg", "jpeg", "png"}:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    object_key = f"avatars/{user_id}_{uuid.uuid4().hex}.{ext}"

    try:
        # самый частый интерфейс: upload_bytes(key, bytes, content_type) -> url
        # если у тебя метод называется иначе — просто переименуй вызов
        avatar_url = await s3_client.upload_bytes(
            object_key=object_key,
            content=profile_data.avatar,
            content_type=avatar.content_type or "application/octet-stream",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to upload avatar. Please try again later.")

    # 8) create profile in db
    new_profile = UserProfileModel(
        user_id=user_id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        gender=profile_data.gender,
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_url,
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return new_profile
