from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.models import User, Role
from app.auth.utils import hash_password, verify_password, create_access_token, create_refresh_token, blacklist_token, verify_token
from app.auth.dependencies import oauth2_scheme
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix='/auth', tags=['auth'])

class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "viewer"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).filter(User.email == user.email))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")
    try:
        role_value = Role[user.role.upper()]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid role")
    db_user = User(email=user.email, pw_hash=hash_password(user.password), role=role_value)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return {"email": db_user.email, "role": db_user.role}

@router.post('/login', response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.pw_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    access_token, access_jti = await create_access_token({'sub': user.email})
    refresh_token, refresh_jti = await create_refresh_token({'sub': user.email})
    return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'bearer'}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: dict, db: AsyncSession = Depends(get_db)):
    payload = await verify_token(data["refresh_token"], "refresh")
    user = await db.execute(select(User).filter(User.email == payload["sub"]))
    user = user.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access_token, access_jti = await create_access_token({"sub": user.email})
    refresh_token, refresh_jti = await create_refresh_token({"sub": user.email})
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl_seconds = max(0, int(payload["exp"]) - now_ts)
    await blacklist_token(payload["jti"], ttl_seconds)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    payload = await verify_token(token, "access")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl_seconds = max(0, int(payload["exp"]) - now_ts)
    await blacklist_token(payload["jti"], ttl_seconds)
    return {"detail": "Logged out"}