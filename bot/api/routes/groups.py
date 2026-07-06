from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from bot.services.database import get_db
from bot.api.auth import get_current_user
from bot.models.models import Group
from bot.services.database import add_group, get_group

router = APIRouter()


class GroupToggle(BaseModel):
    enabled: bool


class GroupAdd(BaseModel):
    chat_id: int
    title: Optional[str] = None


@router.get("")
async def get_groups(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Group))
    items = result.scalars().all()
    return [
        {
            "id": g.id,
            "name": g.title or str(g.chat_id),
            "chat_id": g.chat_id,
            "members": 0,
            "messages": 0,
            "enabled": g.is_active,
            "joinDate": g.created_at.strftime("%Y-%m-%d") if g.created_at else "",
        }
        for g in items
    ]


@router.post("")
async def create_group(
    data: GroupAdd,
    user: dict = Depends(get_current_user),
):
    existing = await get_group(data.chat_id)
    if existing:
        return {"error": "القروب مسجل أصلاً"}
    group = await add_group(chat_id=data.chat_id, title=data.title)
    return {"id": group.id, "chat_id": group.chat_id, "name": group.title, "enabled": group.is_active}


@router.put("/{group_id}/toggle")
async def toggle_group(
    group_id: int,
    data: GroupToggle,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await db.execute(
        update(Group).where(Group.id == group_id).values(is_active=data.enabled)
    )
    await db.commit()
    return {"success": True, "enabled": data.enabled}
