from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from bot.api.database import get_db
from bot.api.auth import get_current_user
from bot.models.models import AutoResponse

router = APIRouter()


class CustomResponseCreate(BaseModel):
    keyword: str
    response: str


class CustomResponseUpdate(BaseModel):
    keyword: Optional[str] = None
    response: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
async def get_custom_responses(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AutoResponse))
    items = result.scalars().all()
    return [
        {
            "id": r.id,
            "keyword": r.keyword,
            "response": r.response,
            "enabled": r.is_active,
        }
        for r in items
    ]


@router.post("")
async def create_custom_response(
    data: CustomResponseCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ar = AutoResponse(keyword=data.keyword, response=data.response, created_by=0)
    db.add(ar)
    await db.commit()
    await db.refresh(ar)
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active}


@router.put("/{response_id}")
async def update_custom_response(
    response_id: int,
    data: CustomResponseUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AutoResponse).where(AutoResponse.id == response_id))
    ar = result.scalar_one_or_none()

    if not ar:
        raise HTTPException(status_code=404, detail="Response not found")

    if data.keyword is not None:
        ar.keyword = data.keyword
    if data.response is not None:
        ar.response = data.response
    if data.enabled is not None:
        ar.is_active = data.enabled

    await db.commit()
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active}


@router.delete("/{response_id}")
async def delete_custom_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await db.execute(delete(AutoResponse).where(AutoResponse.id == response_id))
    await db.commit()
    return {"success": True}
