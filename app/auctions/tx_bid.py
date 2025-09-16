from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Load
from app.models import Item, Bid

async def fetch_item_for_update(db: AsyncSession, item_id: int) -> Item:
    stmt = select(Item).where(Item.id == item_id).with_for_update()
    res = await db.execute(stmt)
    return res.scalars().first()

async def fetch_bids_for_update(db: AsyncSession, item_id: int) -> list[Bid]:
    """Retrieves all bids for an item with row locks"""
    stmt = select(Bid).where(Bid.item_id == item_id).with_for_update()
    res = await db.execute(stmt)
    return list(res.scalars().all())

def check_bid_placed(bids: list[Bid], user_id: int) -> None:
    for bid in bids:
        if bid.user_id == user_id:
            raise HTTPException(status_code=409, detail="User already placed a bid for this item")

def max_cap(bid: Bid) -> float:
    """Calculates a bid’s maximum cap using max_budget or amount"""
    return float(bid.max_budget) if bid.max_budget is not None else bid.amount

def compute_winner(bids: list[Bid], user_id: int, amount: float, max_budget: float | None, bid_increment: float | None) -> tuple[int, float, float | None, float | None]:
    highest = max(bids, key=lambda b: b.amount, default=None)
    current_high = highest.amount if highest else 0.0
    new_amount = float(amount)
    new_max_budget = float(max_budget) if max_budget is not None else None
    new_bid_increment = float(bid_increment) if bid_increment is not None else None
    winner_user_id = user_id
    winner_amount = new_amount
    if highest and new_amount <= current_high:
        defender = highest
        defender_cap = max_cap(defender)
        step = float(defender.bid_increment) if defender.bid_increment is not None else 0.0
        if step > 0 and new_amount >= defender.amount and new_amount < defender_cap:
            winner_user_id = defender.user_id
            winner_amount = min(defender_cap, new_amount + step)
        else:
            raise HTTPException(status_code=400, detail="Bid must exceed current highest")
    else:
        if highest:
            contenders = [b for b in bids if b.user_id != user_id and b.max_budget is not None and b.bid_increment is not None and b.bid_increment > 0]
            if contenders:
                best = max(contenders, key=lambda b: max_cap(b))
                if new_amount <= max_cap(best):
                    winner_user_id = best.user_id
                    winner_amount = min(max_cap(best), new_amount + float(best.bid_increment))
    return winner_user_id, winner_amount, new_max_budget, new_bid_increment

def apply_bid_mutation(db: AsyncSession, bids: list[Bid], item_id: int, winner_user_id: int, actor_user_id: int, winner_amount: float, max_budget: float | None, bid_increment: float | None) -> None:
    """Applies the winning bid by creating or updating a bid in the database"""
    if winner_user_id == actor_user_id:
        bid = Bid(item_id=item_id, user_id=actor_user_id, amount=winner_amount, max_budget=max_budget, bid_increment=bid_increment)
        db.add(bid)
    else:
        for b in bids:
            if b.user_id == winner_user_id:
                b.amount = max(b.amount, winner_amount)
                break

async def place_bid(db: AsyncSession, item_id: int, user_id: int, amount: float, max_budget: float | None, bid_increment: float | None) -> dict:
    item = await fetch_item_for_update(db, item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    now = datetime.now(timezone.utc)

    if item.status != "open" or (item.close_at and item.close_at <= now):
        raise HTTPException(status_code=400, detail="Auction closed")

    bids = await fetch_bids_for_update(db, item_id)
    check_bid_placed(bids, user_id)
    winner_user_id, winner_amount, new_max_budget, new_bid_increment = compute_winner(bids, user_id, amount, max_budget, bid_increment)
    apply_bid_mutation(db, bids, item_id, winner_user_id, user_id, winner_amount, new_max_budget, new_bid_increment)
    await db.flush()
    return {"item_id": item_id, "winner_user_id": winner_user_id, "amount": winner_amount}

