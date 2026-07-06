from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from bot.services.database import get_db
from bot.api.auth import get_current_user
from bot.models.models import User, BannedUser

router = APIRouter()


class BanRequest(BaseModel):
    username: str
    reason: str


@router.get("")
async def get_users(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(User))
    items = result.scalars().all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "first_name": u.first_name,
            "is_subscribed": u.is_subscribed,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in items
    ]


@router.get("/banned")
async def get_banned_users(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(BannedUser))
    items = result.scalars().all()
    return [
        {
            "id": b.id,
            "username": f"@user_{b.telegram_id}",
            "telegram_id": b.telegram_id,
            "reason": b.reason or "",
            "bannedDate": b.banned_at.strftime("%Y-%m-%d") if b.banned_at else "",
            "bannedBy": str(b.banned_by) if b.banned_by else "admin",
        }
        for b in items
    ]


@router.post("/banned")
async def ban_user_endpoint(
    data: BanRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(User).where(User.username == data.username.lstrip("@"))
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    ban = BannedUser(
        telegram_id=target_user.telegram_id,
        reason=data.reason,
        banned_by=user.get("id", 0)
    )
    db.add(ban)
    await db.commit()
    await db.refresh(ban)
    return {
        "id": ban.id,
        "username": data.username,
        "reason": ban.reason,
        "bannedDate": ban.banned_at.strftime("%Y-%m-%d") if ban.banned_at else "",
        "bannedBy": "admin",
    }


@router.delete("/banned/{ban_id}")
async def unban_user(
    ban_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await db.execute(delete(BannedUser).where(BannedUser.id == ban_id))
    await db.commit()
    return {"success": True}
