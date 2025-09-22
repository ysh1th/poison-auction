from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.auth.dependencies import get_current_user
from app.auctions.tx_bid import place_bid
from sqlalchemy import select
from app.models import Item, Bid, OwnedItem, Image, AuctionParticipant, User
from app.core.config import settings
import httpx
from datetime import datetime, timedelta, timezone
import random

router = APIRouter(prefix='/items', tags=['auctions'])

class BidIn(BaseModel):
    amount: float
    max_budget: float | None = None
    bid_increment: float | None = None

@router.post('/{item_id}/bid')
async def bid(item_id: int, body: BidIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # Ensure user joined the room before bidding
    res_join = await db.execute(select(AuctionParticipant).where(AuctionParticipant.item_id == item_id, AuctionParticipant.user_id == user.id))
    if not res_join.scalars().first():
        raise HTTPException(status_code=403, detail="Join the auction before bidding")
    result = await place_bid(db, item_id, user.id, body.amount, body.max_budget, body.bid_increment)
    await db.commit()
    return result

class CreateItemIn(BaseModel):
    title: str
    description: str | None = None
    base_price: float = 0.0
    query: str | None = None  # Unsplash search query

async def fetch_unsplash_image(query: str | None) -> dict | None:
    access_key = settings.unsplash_access_key
    if not access_key:
        return None
    headers = {"Accept-Version": "v1"}
    if query:
        params = {"client_id": access_key, "query": query, "per_page": 1}
        endpoint = "https://api.unsplash.com/search/photos"
    else:
        params = {"client_id": access_key, "count": 1}
        endpoint = "https://api.unsplash.com/photos/random"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(endpoint, headers=headers, params=params)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list):
            if not data:
                return None
            photo = data[0]
        else:
            if not data.get("results"):
                return None
            photo = data["results"][0]
        return {
            "unsplash_id": photo.get("id"),
            "image_url": (photo.get("urls") or {}).get("regular") or (photo.get("urls") or {}).get("full"),
            "image_thumb_url": (photo.get("urls") or {}).get("thumb"),
            "image_attribution": (photo.get("user") or {}).get("name"),
            "image_attribution_link": (photo.get("links") or {}).get("html")
        }

def rand_min_start_price() -> float:
    return float(random.randint(100, 250))

def to_naive_utc(dt: datetime) -> datetime:
    """Convert any datetime to naive UTC (no tzinfo)."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def schedule_times(now: datetime) -> tuple[datetime, datetime]:
    """Return naive UTC start/end for DB columns defined as TIMESTAMP WITHOUT TIME ZONE."""
    base = to_naive_utc(now)
    start_at = base + timedelta(seconds=10)
    end_at = start_at + timedelta(seconds=30)
    return start_at, end_at

async def upsert_image(db: AsyncSession, query: str | None) -> int | None:
    img = await fetch_unsplash_image(query)
    if not img:
        return None
    existing = await db.execute(select(Image).where(Image.unsplash_id == img.get("unsplash_id")))
    existing_img = existing.scalars().first()
    if existing_img:
        return existing_img.id
    new_img = Image(
        unsplash_id=img.get("unsplash_id"),
        image_url=img.get("image_url"),
        image_thumb_url=img.get("image_thumb_url"),
        image_attribution=img.get("image_attribution"),
        image_attribution_link=img.get("image_attribution_link"),
    )
    db.add(new_img)
    await db.flush()
    return new_img.id

@router.post('')
async def create_item(body: CreateItemIn, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    image_id = await upsert_image(db, body.query)
    start_at, end_at = schedule_times(now)
    item = Item(
        title=body.title,
        description=body.description or "",
        base_price=body.base_price,
        start_at=start_at,
        end_at=end_at,
        min_start_price=rand_min_start_price(),
        status="scheduled",
        image_id=image_id,
    )
    db.add(item)
    await db.flush()
    await db.commit()
    return {"id": item.id}

def serialize_current_bid(bids: list[Bid]) -> dict | None:
    if not bids:
        return None
    highest = max(bids, key=lambda b: b.amount)
    return {"amount": highest.amount, "user_id": highest.user_id}

def _aware(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware (UTC) for safe arithmetic.
    If None, returns None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def compute_status_and_timers(item: Item, now: datetime) -> tuple[str, int | None, int | None]:
    """Returns (status, seconds_to_start, seconds_to_end) and may imply transitions handled elsewhere."""
    seconds_to_start = None
    seconds_to_end = None
    status = item.status
    start_at = _aware(item.start_at)
    end_at = _aware(item.end_at)
    if start_at and now < start_at:
        status = "scheduled"
        seconds_to_start = max(0, int((start_at - now).total_seconds()))
    elif end_at and now < end_at:
        status = "in_progress"
        seconds_to_end = max(0, int((end_at - now).total_seconds()))
    else:
        status = "closed"
    return status, seconds_to_start, seconds_to_end

async def ensure_transition_and_spawn_next(db: AsyncSession, item: Item, now: datetime) -> bool:
    """If an item transitions, mutate in-memory and flush only. Return True if mutated.
    Caller is responsible for committing."""
    mutated = False
    # Read prior status without triggering lazy-load on expired attributes
    prior = item.__dict__.get('status', None)
    status, _, _ = compute_status_and_timers(item, now)
    if status != prior:
        item.status = status
        mutated = True
        await db.flush()
        # When entering in_progress, create the next scheduled item immediately
        if status == "in_progress":
            start_at, end_at = schedule_times(now)
            next_item = Item(
                title=f"Next: {item.title}",
                description=item.description,
                base_price=item.base_price,
                start_at=start_at,
                end_at=end_at,
                min_start_price=rand_min_start_price(),
                status="scheduled",
                image_id=item.image_id,
            )
            db.add(next_item)
            mutated = True
        # When becoming closed, finalize winner and award
        if status == "closed":
            res_b = await db.execute(select(Bid).where(Bid.item_id == item.id))
            bids = list(res_b.scalars().all())
            if bids:
                winner = max(bids, key=lambda b: b.amount)
                # Deduct balance from winner only
                res_u = await db.execute(select(User).where(User.id == winner.user_id))
                u = res_u.scalars().first()
                if u:
                    u.balance = float(u.balance or 0.0) - float(winner.amount)
                    mutated = True
                # Snapshot image data
                image = None
                if item.image_id:
                    res_img = await db.execute(select(Image).where(Image.id == item.image_id))
                    image = res_img.scalars().first()
                owned = OwnedItem(
                    user_id=winner.user_id,
                    item_id=item.id,
                    image_url=image.image_url if image else None,
                    image_thumb_url=image.image_thumb_url if image else None,
                    image_attribution=image.image_attribution if image else None,
                    image_attribution_link=image.image_attribution_link if image else None,
                    unsplash_id=image.unsplash_id if image else None,
                )
                db.add(owned)
                mutated = True
        await db.flush()
    return mutated

@router.get('/{item_id}')
async def get_item(item_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    now = datetime.now(timezone.utc)
    changed = await ensure_transition_and_spawn_next(db, item, now)
    if changed:
        await db.commit()
    res_b = await db.execute(select(Bid).where(Bid.item_id == item_id))
    bids = list(res_b.scalars().all())
    # Load image if any
    image = None
    if item.image_id:
        res_img = await db.execute(select(Image).where(Image.id == item.image_id))
        image = res_img.scalars().first()

    status, secs_start, secs_end = compute_status_and_timers(item, now)
    # Presence count from participants table (no spectate during in_progress)
    res_p = await db.execute(select(AuctionParticipant).where(AuctionParticipant.item_id == item_id))
    participants = list(res_p.scalars().all())
    joined = any(p.user_id == user.id for p in participants)
    if status == "in_progress" and not joined:
        raise HTTPException(status_code=403, detail="Auction in progress. Access denied.")

    # Placeholder image if none
    image_payload = (
        {
            "id": image.id,
            "unsplash_id": image.unsplash_id,
            "image_url": image.image_url,
            "image_thumb_url": image.image_thumb_url,
            "image_attribution": image.image_attribution,
            "image_attribution_link": image.image_attribution_link,
        } if image else {
            "image_url": f"https://picsum.photos/seed/item-{item.id}/600/400",
            "image_thumb_url": f"https://picsum.photos/seed/item-{item.id}/200/150"
        }
    )

    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "base_price": item.base_price,
        "status": status,
        "start_at": item.start_at.isoformat() if item.start_at else None,
        "end_at": item.end_at.isoformat() if item.end_at else None,
        "min_start_price": item.min_start_price,
        "image": image_payload,
        "current_bid": serialize_current_bid(bids),
        "seconds_to_start": secs_start,
        "seconds_to_end": secs_end,
        "players": len(participants),
        "joined": joined,
    }

@router.post('/{item_id}/close')
async def close_auction(item_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    now = datetime.now(timezone.utc)
    await ensure_transition_and_spawn_next(db, item, now)
    if item.status != "in_progress" and item.status != "closed":
        # Only allow close when in_progress or already closed
        return {"status": item.status}
    res_b = await db.execute(select(Bid).where(Bid.item_id == item_id))
    bids = list(res_b.scalars().all())
    if not bids:
        item.status = "closed"
        await db.flush()
        await db.commit()
        return {"status": "closed", "winner": None}
    winner = max(bids, key=lambda b: b.amount)
    # Deduct balance from winner only
    res_u = await db.execute(select(User).where(User.id == winner.user_id))
    u = res_u.scalars().first()
    if u:
        u.balance = float(u.balance or 0.0) - float(winner.amount)
    # Snapshot image data from Image table
    image = None
    if item.image_id:
        res_img = await db.execute(select(Image).where(Image.id == item.image_id))
        image = res_img.scalars().first()
    owned = OwnedItem(
        user_id=winner.user_id,
        item_id=item.id,
        image_url=image.image_url if image else None,
        image_thumb_url=image.image_thumb_url if image else None,
        image_attribution=image.image_attribution if image else None,
        image_attribution_link=image.image_attribution_link if image else None,
        unsplash_id=image.unsplash_id if image else None,
    )
    db.add(owned)
    item.status = "closed"
    await db.flush()
    await db.commit()
    return {"status": "closed", "winner_user_id": winner.user_id, "amount": winner.amount, "owned_item_id": owned.id}


# Listing and state endpoints

@router.get('')
async def list_items(status: str | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    res = await db.execute(select(Item))
    items = list(res.scalars().all())
    now = datetime.now(timezone.utc)
    rows = []
    any_changed = False
    for it in items:
        changed = await ensure_transition_and_spawn_next(db, it, now)
        any_changed = any_changed or changed
        st, secs_s, secs_e = compute_status_and_timers(it, now)
        # Skip closed items after 2 minutes (don't show in lobby)
        if st == "closed":
            ref_ts = _aware(it.end_at) or _aware(it.created_at) or now
            age = (now - ref_ts).total_seconds()
            if age > 120:
                # Skip old closed items instead of deleting (avoids FK constraints)
                continue
        if status and st != status:
            continue
        res_b = await db.execute(select(Bid).where(Bid.item_id == it.id))
        bids = list(res_b.scalars().all())
        current = serialize_current_bid(bids)
        res_p = await db.execute(select(AuctionParticipant).where(AuctionParticipant.item_id == it.id))
        players = len(list(res_p.scalars().all()))
        # Load image if present
        image_url = None
        image_thumb_url = None
        if it.image_id:
            res_img = await db.execute(select(Image).where(Image.id == it.image_id))
            img = res_img.scalars().first()
            if img:
                image_url = img.image_url
                image_thumb_url = img.image_thumb_url
        # Placeholder fallback if missing
        if not image_thumb_url and not image_url:
            image_thumb_url = f"https://picsum.photos/seed/{it.id}/200/150"
        # Sort priority
        priority = 0 if st == "in_progress" else 1 if st == "scheduled" else 2
        sort_key = secs_e if st == "in_progress" else secs_s if st == "scheduled" else 1e9
        rows.append((priority, sort_key if sort_key is not None else 1e9, {
            "id": it.id,
            "title": it.title,
            "status": st,
            "start_at": it.start_at.isoformat() if it.start_at else None,
            "end_at": it.end_at.isoformat() if it.end_at else None,
            "seconds_to_start": secs_s,
            "seconds_to_end": secs_e,
            "min_start_price": it.min_start_price,
            "base_price": it.base_price,
            "current_bid": current,
            "players": players,
            "image": {"image_url": image_url, "image_thumb_url": image_thumb_url},
        }))
    # If there are no scheduled or in_progress items, seed one
    if not any(r[2]["status"] in ("scheduled", "in_progress") for r in rows):
        # Seed a new scheduled item
        title = f"Mystery {now.strftime('%H%M%S')}"
        start_at, end_at = schedule_times(now)
        seed = Item(
            title=title,
            description="Auto-seeded",
            base_price=10.0,
            start_at=start_at,
            end_at=end_at,
            min_start_price=rand_min_start_price(),
            status="scheduled",
            image_id=None,
        )
        db.add(seed)
        await db.flush()
        # append seeded to rows with placeholder image
        rows.append((1, 10, {
            "id": seed.id,
            "title": seed.title,
            "status": "scheduled",
            "start_at": seed.start_at.isoformat(),
            "end_at": seed.end_at.isoformat(),
            "seconds_to_start": max(0, int((_aware(seed.start_at) - now).total_seconds())),
            "seconds_to_end": None,
            "min_start_price": seed.min_start_price,
            "base_price": seed.base_price,
            "current_bid": None,
            "players": 0,
            "image": {"image_thumb_url": f"https://picsum.photos/seed/{seed.id}/200/150"}
        }))
        await db.commit()

    # Sort and limit to 10
    # Commit any changes from transitions/seeding
    if any_changed:
        await db.commit()

    rows.sort(key=lambda r: (r[0], r[1]))
    out = [r[2] for r in rows[:10]]
    return out


class JoinLeaveOut(BaseModel):
    joined: bool

@router.post('/{item_id}/join', response_model=JoinLeaveOut)
async def join_item(item_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    now = datetime.now(timezone.utc)
    status, _, _ = compute_status_and_timers(item, now)
    if status != "scheduled":
        raise HTTPException(status_code=403, detail="Auction locked")
    existing = await db.execute(select(AuctionParticipant).where(AuctionParticipant.item_id == item_id, AuctionParticipant.user_id == user.id))
    if not existing.scalars().first():
        db.add(AuctionParticipant(item_id=item_id, user_id=user.id))
        await db.flush()
        await db.commit()
    return {"joined": True}

@router.post('/{item_id}/leave', response_model=JoinLeaveOut)
async def leave_item(item_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # Soft leave: delete participant record; user can re-join only if scheduled
    res = await db.execute(select(AuctionParticipant).where(AuctionParticipant.item_id == item_id, AuctionParticipant.user_id == user.id))
    p = res.scalars().first()
    if p:
        await db.delete(p)
        await db.commit()
    return {"joined": False}


@router.get('/active')
async def get_active(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    res = await db.execute(select(Item))
    items = list(res.scalars().all())
    # Prefer in_progress, else nearest scheduled
    in_prog = []
    scheduled = []
    for it in items:
        st, _, _ = compute_status_and_timers(it, now)
        if st == "in_progress":
            in_prog.append(it)
        elif st == "scheduled":
            scheduled.append(it)
    if in_prog:
        it = in_prog[0]
        return {"id": it.id}
    if scheduled:
        it = sorted(scheduled, key=lambda x: x.start_at or now)[0]
        return {"id": it.id}
    return None


