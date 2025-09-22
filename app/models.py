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
    role = Column(Enum(Role, native_enum=False), default=Role.VIEWER)
    # Virtual wallet balance credited on registration
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    # Auction scheduling
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    # Minimum price required to start bidding
    min_start_price = Column(Float, default=100.0)
    base_price = Column(Float)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=func.now())
    image_id = Column(Integer, ForeignKey("images.id"), nullable=True)


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    unsplash_id = Column(String, unique=True, nullable=True, index=True)
    image_url = Column(String, nullable=True)
    image_thumb_url = Column(String, nullable=True)
    image_attribution = Column(String, nullable=True)
    image_attribution_link = Column(String, nullable=True)


class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    max_budget = Column(Float, nullable=True)
    bid_increment = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("item_id", "user_id", name="unique_bid"),)


class OwnedItem(Base):
    __tablename__ = "owned_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    item_id = Column(Integer, ForeignKey("items.id"), index=True)
    acquired_at = Column(DateTime, default=func.now())
    # Snapshot of image data
    image_url = Column(String, nullable=True)
    image_thumb_url = Column(String, nullable=True)
    image_attribution = Column(String, nullable=True)
    image_attribution_link = Column(String, nullable=True)
    unsplash_id = Column(String, nullable=True)


class AuctionParticipant(Base):
    __tablename__ = "auction_participants"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    joined_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint("item_id", "user_id", name="unique_participant"),)