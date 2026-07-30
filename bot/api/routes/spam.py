from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.services.database import get_db, get_all_spam_patterns, delete_spam_pattern, save_spam_pattern
from bot.models.models import SpamPattern
from pydantic import BaseModel

router = APIRouter()

class SpamPatternCreate(BaseModel):
    content: str

@router.get("")
async def get_patterns(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(SpamPattern)
    count_query = select(func.count()).select_from(SpamPattern)

    if search:
        search_filter = SpamPattern.content.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(SpamPattern.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [{"id": p.id, "content": p.content, "created_at": str(p.created_at)} for p in items],
        "total": total,
        "page": page,
        "limit": limit,
    }

@router.post("")
async def create_pattern(data: SpamPatternCreate, db: AsyncSession = Depends(get_db)):
    await save_spam_pattern(data.content)
    return {"status": "ok"}

@router.delete("/{pattern_id}")
async def delete_pattern(pattern_id: int, db: AsyncSession = Depends(get_db)):
    await delete_spam_pattern(pattern_id)
    return {"status": "ok"}
