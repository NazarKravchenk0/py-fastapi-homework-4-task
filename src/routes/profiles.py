from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.exceptions.storage import S3FileUploadError
from src.models.profiles import ProfileModel
from src.models.users import UserModel
from src.schemas.profiles import ProfileCreateSchema, ProfileResponseSchema
from src.security.auth import get_current_user
from src.storages.s3 import S3Storage

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def _is_admin(user: UserModel) -> bool:
    return getattr(user, "group_id", None) == 3


async def get_s3_storage() -> S3Storage:
    return S3Storage()


@router.post(
    "/users/{user_id}/profile/",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileResponseSchema,
)
async def create_profile(
    user_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),
    info: str = Form(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    storage: S3Storage = Depends(get_s3_storage),
) -> ProfileResponseSchema:
    # ✅ required: user from path must exist and be active
    stmt_user = select(UserModel).where(UserModel.id == user_id)
    target_user = (await db.execute(stmt_user)).scalars().first()
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )

    # permissions (exact message required)
    if current_user.id != user_id and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile.",
        )

    # cannot create twice
    stmt_existing = select(ProfileModel).where(ProfileModel.user_id == user_id)
    existing = (await db.execute(stmt_existing)).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists")

    avatar_bytes = await avatar.read()

    # ✅ validation via schema (task requirement)
    try:
        payload = ProfileCreateSchema(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar_bytes,
            avatar_content_type=avatar.content_type,
        )
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile data.",
        )

    try:
        avatar_key = f"avatars/{user_id}_avatar.jpg"
        avatar_url = await storage.upload_file(
            key=avatar_key,
            content=payload.avatar,
            content_type=payload.avatar_content_type,
        )
    except S3FileUploadError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        )

    profile = ProfileModel(
        user_id=user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        gender=payload.gender,
        date_of_birth=payload.birth_date,  # см. ниже: поле в схеме
        info=payload.info,
        avatar_url=avatar_url,
    )

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return ProfileResponseSchema.model_validate(profile)
