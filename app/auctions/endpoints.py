from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.auth.dependencies import get_current_user
from app.auctions.tx_bid import place_bid

router = APIRouter(prefix='/items', tags=['auctions'])

class BidIn(BaseModel):
    amount: float
    poison_budget: float | None = None
    poison_step: float | None = None

@router.post('/{item_id}/bid')
async def bid(item_id: int, body: BidIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await place_bid(db, item_id, user.id, body.amount, body.poison_budget, body.poison_step)
    await db.commit()
    return result

