from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.db import Base
import enum
from datetime import datetime

class Role(enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key = True, index=True)
    email = Column(String, unique=True, index=True)
    pw_hash = Column(String)
    role = Column(Enum(Role), default=Role.VIEWER)
    created_at = Column(DateTime, default=func.now())


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    desc = Column(String)
    close_at = Column(DateTime)
    base_price = Column(Float)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=func.now())

