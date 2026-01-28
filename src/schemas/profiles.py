import re
from datetime import date, datetime
from pydantic import BaseModel, field_validator, ConfigDict

_ALLOWED_GENDERS = {"man", "woman"}
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
_MAX_AVATAR_SIZE = 1 * 1024 * 1024


class ProfileCreateSchema(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: str
    info: str
    avatar: bytes
    avatar_content_type: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z]+", value or ""):
            raise ValueError(f"{value} contains non-english letters")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        if value not in _ALLOWED_GENDERS:
            raise ValueError("Invalid gender")
        return value

    @field_validator("info")
    @classmethod
    def validate_info(cls, value: str) -> str:
        if value is None or not value.strip():
            raise ValueError("Info field cannot be empty")
        return value

    @field_validator("avatar_content_type")
    @classmethod
    def validate_avatar_type(cls, value: str) -> str:
        if value not in _ALLOWED_IMAGE_TYPES:
            raise ValueError("Invalid image format")
        return value

    @field_validator("avatar")
    @classmethod
    def validate_avatar_size(cls, value: bytes) -> bytes:
        if len(value) > _MAX_AVATAR_SIZE:
            raise ValueError("Image size exceeds the allowed limit (1MB).")
        return value

    @property
    def birth_date(self) -> date:
        birth = datetime.strptime(self.date_of_birth, "%Y-%m-%d").date()
        if birth.year <= 1900:
            raise ValueError("Invalid birth date - year must be greater than 1900.")
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < 18:
            raise ValueError("You must be at least 18 years old to register.")
        return birth
