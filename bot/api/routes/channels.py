from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from telegram import Bot
import os
import json
from collections import defaultdict
from ...models.models import News, ScheduledPost, StudyPlan, ChannelGroup
from ...services.database import (
    get_all_channel_groups, get_active_channel_groups,
    add_channel_group, toggle_channel_group,
    update_channel_group, delete_channel_group,
    get_channel_group_by_chat_id, async_session,
    set_official_channel
)

router = APIRouter()


async def build_post_counts():
    """Load all post tables once, return {chat_id_str: count}."""
    counts = defaultdict(int)
    async with async_session() as session:
        from sqlalchemy import select

        # News: count if chat_id is a key in group_message_ids dict or in target_channels list
        for group_msg_ids, target_channels in await session.execute(
            select(News.group_message_ids, News.target_channels).where(News.is_published == True)
        ):
            for cid in _extract_chat_ids_from_pair(group_msg_ids, target_channels):
                counts[cid] += 1

        # Scheduled posts: same logic
        for group_msg_ids, target_channels in await session.execute(
            select(ScheduledPost.group_message_ids, ScheduledPost.target_channels).where(ScheduledPost.is_published == True)
        ):
            for cid in _extract_chat_ids_from_pair(group_msg_ids, target_channels):
                counts[cid] += 1

        # Study plans: count from target_channels list + channel_message_id for official channel
        channel_chat_id = (await session.execute(
            select(ChannelGroup.chat_id).where(ChannelGroup.type == 'channel', ChannelGroup.is_active == True).limit(1)
        )).scalar_one_or_none()
        official_cid_str = str(channel_chat_id) if channel_chat_id else None

        for channel_msg_id, target_channels in await session.execute(
            select(StudyPlan.channel_message_id, StudyPlan.target_channels).where(StudyPlan.is_active == True)
        ):
            # Count if chat_id is in target_channels
            counted_cids = _extract_chat_ids_from_list(target_channels)
            for cid in counted_cids:
                counts[cid] += 1
            # If not in target_channels but has channel_message_id, count for official channel
            if official_cid_str and official_cid_str not in counted_cids and channel_msg_id:
                counts[official_cid_str] += 1

    return dict(counts)


def _extract_chat_ids_from_pair(group_msg_ids, target_channels):
    """Extract chat_ids from a pair of group_message_ids (dict) + target_channels (list)."""
    chat_ids = set()
    if group_msg_ids:
        try:
            parsed = json.loads(group_msg_ids) if isinstance(group_msg_ids, str) else group_msg_ids
            if isinstance(parsed, dict):
                chat_ids.update(parsed.keys())
        except Exception:
            pass
    if target_channels:
        try:
            parsed = json.loads(target_channels) if isinstance(target_channels, str) else target_channels
            if isinstance(parsed, list):
                chat_ids.update(str(t) for t in parsed)
        except Exception:
            pass
    return chat_ids


def _extract_chat_ids_from_list(target_channels):
    """Extract chat_ids from target_channels list string."""
    if not target_channels:
        return set()
    try:
        parsed = json.loads(target_channels) if isinstance(target_channels, str) else target_channels
        if isinstance(parsed, list):
            return set(str(t) for t in parsed)
    except Exception:
        pass
    return set()

class ChannelGroupCreate(BaseModel):
    chat_id: int
    title: str
    type: str = "group"  # "channel" or "group"
    member_count: int = 0
    invite_link: Optional[str] = None

class ChannelGroupUpdate(BaseModel):
    title: Optional[str] = None
    member_count: Optional[int] = None
    invite_link: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("")
async def get_channel_groups(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200), search: str = Query(None)):
    from sqlalchemy import select
    async with async_session() as session:
        stmt = select(ChannelGroup)
        if search:
            stmt = stmt.where(ChannelGroup.title.ilike(f"%{search}%"))
        result = await session.execute(stmt)
        groups = result.scalars().all()
    post_counts = await build_post_counts()
    result = []
    for g in groups:
        result.append({
            "id": g.id,
            "chatId": g.chat_id,
            "title": g.title,
            "type": g.type,
            "memberCount": g.member_count,
            "inviteLink": g.invite_link,
            "isActive": g.is_active,
            "isOfficial": g.is_official,
            "postCount": post_counts.get(str(g.chat_id), 0),
            "createdAt": g.created_at.isoformat() if g.created_at else None
        })
    total = len(result)
    start = (page - 1) * limit
    return {"items": result[start:start + limit], "total": total, "page": page, "limit": limit}

@router.get("/active")
async def get_active_channel_groups_endpoint():
    groups = await get_active_channel_groups()
    post_counts = await build_post_counts()
    result = []
    for g in groups:
        result.append({
            "id": g.id,
            "chatId": g.chat_id,
            "title": g.title,
            "type": g.type,
            "memberCount": g.member_count,
            "inviteLink": g.invite_link,
            "isActive": g.is_active,
            "postCount": post_counts.get(str(g.chat_id), 0),
        })
    return result

@router.post("")
async def create_channel_group(data: ChannelGroupCreate):
    if data.type not in ["channel", "group"]:
        raise HTTPException(status_code=400, detail="Type must be 'channel' or 'group'")
    group = await add_channel_group(data.chat_id, data.title, data.type, data.member_count, data.invite_link)
    if not group:
        raise HTTPException(status_code=400, detail="Chat ID already exists")
    return {
        "id": group.id,
        "chatId": group.chat_id,
        "title": group.title,
        "type": group.type,
        "memberCount": group.member_count,
        "inviteLink": group.invite_link,
        "isActive": group.is_active,
    }

@router.put("/{group_id}")
async def update_channel_group_endpoint(group_id: int, data: ChannelGroupUpdate):
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    group = await update_channel_group(group_id, **update_data)
    if not group:
        raise HTTPException(status_code=404, detail="Channel/Group not found")
    
    # If title was updated, also update on Telegram
    if data.title:
        try:
            bot_token = os.getenv("BOT_TOKEN")
            bot = Bot(token=bot_token)
            await bot.set_chat_title(group.chat_id, data.title)
        except Exception as e:
            # Log but don't fail - the database update succeeded
            pass
    
    return {
        "id": group.id,
        "chatId": group.chat_id,
        "title": group.title,
        "type": group.type,
        "memberCount": group.member_count,
        "inviteLink": group.invite_link,
        "isActive": group.is_active,
    }

@router.put("/{group_id}/toggle")
async def toggle_channel_group_endpoint(group_id: int):
    group = await toggle_channel_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Channel/Group not found")
    return {
        "id": group.id,
        "chatId": group.chat_id,
        "title": group.title,
        "type": group.type,
        "isActive": group.is_active,
    }

@router.post("/{group_id}/official")
async def set_official_channel_endpoint(group_id: int):
    result = await set_official_channel(group_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Channel/Group not found")
    if result is False:
        raise HTTPException(status_code=400, detail="Only channels (type='channel') can be set as official")
    return {
        "id": result.id,
        "chatId": result.chat_id,
        "title": result.title,
        "type": result.type,
        "isActive": result.is_active,
        "isOfficial": result.is_official,
    }

@router.delete("/{group_id}")
async def delete_channel_group_endpoint(group_id: int):
    success = await delete_channel_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Channel/Group not found")
    return {"message": "Deleted successfully"}

@router.post("/fetch-info")
async def fetch_channel_group_info(data: ChannelGroupCreate):
    """Fetch info from Telegram API - placeholder for now"""
    # This will be implemented to call Telegram API
    # For now, just save with provided data
    group = await add_channel_group(data.chat_id, data.title, data.type, data.member_count, data.invite_link)
    if not group:
        existing = await get_channel_group_by_chat_id(data.chat_id)
        if existing:
            return {
                "id": existing.id,
                "chatId": existing.chat_id,
                "title": existing.title,
                "type": existing.type,
                "memberCount": existing.member_count,
                "inviteLink": existing.invite_link,
                "isActive": existing.is_active,
            }
        raise HTTPException(status_code=400, detail="Failed to add channel/group")
    return {
        "id": group.id,
        "chatId": group.chat_id,
        "title": group.title,
        "type": group.type,
        "memberCount": group.member_count,
        "inviteLink": group.invite_link,
        "isActive": group.is_active,
    }
