from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.auth.dependencies import get_current_user
from app.auctions.tx_bid import place_bid
from sqlalchemy import select
from app.models import Item, Bid, OwnedItem, Image
from app.core.config import settings
import httpx

router = APIRouter(prefix='/items', tags=['auctions'])

class BidIn(BaseModel):
    amount: float
    max_budget: float | None = None
    bid_increment: float | None = None

@router.post('/{item_id}/bid')
async def bid(item_id: int, body: BidIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await place_bid(db, item_id, user.id, body.amount, body.max_budget, body.bid_increment)
    await db.commit()
    return result

class CreateItemIn(BaseModel):
    title: str
    description: str | None = None
    base_price: float = 0.0
    close_at: str | None = None  # ISO datetime string; keep simple for now
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

@router.post('')
async def create_item(body: CreateItemIn, db: AsyncSession = Depends(get_db)):
    # Allow unauthenticated creation for tests; tighten later with auth
    img = await fetch_unsplash_image(body.query)
    image_id = None
    if img:
        # Deduplicate on unsplash_id
        existing = await db.execute(select(Image).where(Image.unsplash_id == img.get("unsplash_id")))
        existing_img = existing.scalars().first()
        if existing_img:
            image_id = existing_img.id
        else:
            new_img = Image(
                unsplash_id=img.get("unsplash_id"),
                image_url=img.get("image_url"),
                image_thumb_url=img.get("image_thumb_url"),
                image_attribution=img.get("image_attribution"),
                image_attribution_link=img.get("image_attribution_link"),
            )
            db.add(new_img)
            await db.flush()
            image_id = new_img.id

    item = Item(
        title=body.title,
        description=body.description or "",
        base_price=body.base_price,
        close_at=None,
        status="open",
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

@router.get('/{item_id}')
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    res_b = await db.execute(select(Bid).where(Bid.item_id == item_id))
    bids = list(res_b.scalars().all())
    # Load image if any
    image = None
    if item.image_id:
        res_img = await db.execute(select(Image).where(Image.id == item.image_id))
        image = res_img.scalars().first()

    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "base_price": item.base_price,
        "status": item.status,
        "image": (
            {
                "id": image.id,
                "unsplash_id": image.unsplash_id,
                "image_url": image.image_url,
                "image_thumb_url": image.image_thumb_url,
                "image_attribution": image.image_attribution,
                "image_attribution_link": image.image_attribution_link,
            } if image else None
        ),
        "current_bid": serialize_current_bid(bids)
    }

@router.post('/{item_id}/close')
async def close_auction(item_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.status != "open":
        return {"status": item.status}
    res_b = await db.execute(select(Bid).where(Bid.item_id == item_id))
    bids = list(res_b.scalars().all())
    if not bids:
        item.status = "closed"
        await db.flush()
        await db.commit()
        return {"status": "closed", "winner": None}
    winner = max(bids, key=lambda b: b.amount)
    owned = OwnedItem(
        user_id=winner.user_id,
        item_id=item.id,
        image_url=getattr(item, 'image_url', None),
        image_thumb_url=getattr(item, 'image_thumb_url', None),
        image_attribution=getattr(item, 'image_attribution', None),
        image_attribution_link=getattr(item, 'image_attribution_link', None),
        unsplash_id=getattr(item, 'unsplash_id', None),
    )
    db.add(owned)
    item.status = "closed"
    await db.flush()
    await db.commit()
    return {"status": "closed", "winner_user_id": winner.user_id, "amount": winner.amount, "owned_item_id": owned.id}


