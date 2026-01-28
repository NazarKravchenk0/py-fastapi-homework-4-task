from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, ExpiredSignatureError

from config import get_jwt_auth_manager
from database import UserModel, get_db
from security.http import get_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = get_token(request)
    jwt_manager = get_jwt_auth_manager()

    try:
        payload = jwt_manager.decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    stmt = select(UserModel).where(UserModel.id == int(user_id))
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    return user
