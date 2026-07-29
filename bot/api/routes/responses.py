from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from bot.services.database import get_db
from bot.api.auth import get_current_user
from bot.models.models import AutoResponse
from bot.services.database import add_auto_response, update_auto_response

router = APIRouter()


class CustomResponseCreate(BaseModel):
    keyword: str
    response: str
    news_id: Optional[int] = None


class CustomResponseUpdate(BaseModel):
    keyword: Optional[str] = None
    response: Optional[str] = None
    enabled: Optional[bool] = None
    news_id: Optional[int] = None


@router.get("")
async def get_custom_responses(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(AutoResponse.id)))).scalar() or 0
    result = await db.execute(
        select(AutoResponse).offset((page - 1) * limit).limit(limit)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "keyword": r.keyword,
                "response": r.response,
                "enabled": r.is_active,
                "news_id": r.news_id,
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("")
async def create_custom_response(
    data: CustomResponseCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ar = await add_auto_response(
        keyword=data.keyword, response=data.response, created_by=0, news_id=data.news_id,
    )
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active, "news_id": ar.news_id}


@router.put("/{response_id}")
async def update_custom_response(
    response_id: int,
    data: CustomResponseUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ar = await update_auto_response(
        response_id=response_id,
        keyword=data.keyword,
        response=data.response,
        is_active=data.enabled,
        news_id=data.news_id,
    )
    if not ar:
        raise HTTPException(status_code=404, detail="Response not found")
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active, "news_id": ar.news_id}


@router.delete("")
async def delete_all_responses(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await db.execute(delete(AutoResponse))
    await db.commit()
    return {"success": True}


@router.delete("/{response_id}")
async def delete_custom_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await db.execute(delete(AutoResponse).where(AutoResponse.id == response_id))
    await db.commit()
    return {"success": True}
