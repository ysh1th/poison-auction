from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Load
from app.models import Item, Bid

async def place_bid(db: AsyncSession, item_id: int, user_id: int, amount: float, poison_budget: float | None, poison_step: float | None) -> dict:
    item_stmt = select(Item).where(Item.id == item_id).with_for_update()
    item_res = await db.execute(item_stmt)
    item = item_res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    now = datetime.now(timezone.utc)
    if item.status != "open" or (item.close_at and item.close_at <= now):
        raise HTTPException(status_code=400, detail="Auction closed")

    bids_stmt = select(Bid).where(Bid.item_id == item_id).with_for_update()
    bids_res = await db.execute(bids_stmt)
    bids = list(bids_res.scalars().all())

    for b in bids:
        if b.user_id == user_id:
            raise HTTPException(status_code=409, detail="User already placed a bid for this item")

    highest = max(bids, key=lambda b: b.amount, default=None)
    current_high = highest.amount if highest else 0.0

    new_amount = float(amount)
    new_poison_budget = float(poison_budget) if poison_budget is not None else None
    new_poison_step = float(poison_step) if poison_step is not None else None

    def max_cap(b: Bid) -> float:
        return float(b.poison_budget) if b.poison_budget is not None else b.amount

    winner_user_id = user_id
    winner_amount = new_amount

    if highest and new_amount <= current_high:
        defender = highest
        defender_cap = max_cap(defender)
        step = float(defender.poison_step) if defender.poison_step is not None else 0.0
        if step > 0 and new_amount >= defender.amount and new_amount < defender_cap:
            winner_user_id = defender.user_id
            winner_amount = min(defender_cap, new_amount + step)
        else:
            raise HTTPException(status_code=400, detail="Bid must exceed current highest")
    else:
        if highest:
            contenders = [b for b in bids if b.user_id != user_id and b.poison_budget is not None and b.poison_step is not None and b.poison_step > 0]
            if contenders:
                best = max(contenders, key=lambda b: max_cap(b))
                if new_amount <= max_cap(best):
                    winner_user_id = best.user_id
                    winner_amount = min(max_cap(best), new_amount + float(best.poison_step))

    if winner_user_id == user_id:
        bid = Bid(item_id=item_id, user_id=user_id, amount=winner_amount, poison_budget=new_poison_budget, poison_step=new_poison_step)
        db.add(bid)
    else:
        for b in bids:
            if b.user_id == winner_user_id:
                b.amount = max(b.amount, winner_amount)
                break
    await db.flush()
    return {"item_id": item_id, "winner_user_id": winner_user_id, "amount": winner_amount}

