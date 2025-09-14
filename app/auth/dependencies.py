from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.models import User
from app.auth.utils import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = await verify_token(token, "access")
    email = payload.get("sub")
    user = await db.execute(select(User).filter(User.email == email))
    user = user.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def require_role(role: str):
    async def role_checker(user=Depends(get_current_user)):
        if user.role.value != role and user.role.value != "admin":
            raise HTTPException(status_code=403, detail=f'{role.capitalize()} role required')
        return user
    return role_checker