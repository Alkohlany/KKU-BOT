from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from telegram import Bot
import os
import json
from ...models.models import News, ScheduledPost, StudyPlan, ChannelGroup
from ...services.database import (
    get_all_channel_groups, get_active_channel_groups, 
    add_channel_group, toggle_channel_group, 
    update_channel_group, delete_channel_group,
    get_channel_group_by_chat_id, async_session,
    set_official_channel
)

router = APIRouter()

async def count_posts_for_chat(chat_id):
    """Count how many posts are published to a specific chat_id from the dashboard"""
    async with async_session() as session:
        from sqlalchemy import select
        count = 0
        chat_id_str = str(chat_id)
        
        # 1. Count from News (published posts with group_message_ids)
        news_result = await session.execute(
            select(News.group_message_ids, News.channel_message_id, News.is_published, News.target_channels)
        )
        for row in news_result:
            group_msg_ids, channel_msg_id, is_published, target_channels = row
            if not is_published:
                continue
            # Check group_message_ids
            if group_msg_ids:
                try:
                    group_ids = json.loads(group_msg_ids) if isinstance(group_msg_ids, str) else group_msg_ids
                    if chat_id_str in group_ids:
                        count += 1
                        continue
                except:
                    pass
            # Check target_channels
            if target_channels:
                try:
                    targets = json.loads(target_channels) if isinstance(target_channels, str) else target_channels
                    if chat_id in targets or chat_id_str in [str(t) for t in targets]:
                        count += 1
                        continue
                except:
                    pass
        
        # 2. Count from Scheduled Posts (published)
        scheduled_result = await session.execute(
            select(ScheduledPost.group_message_ids, ScheduledPost.is_published, ScheduledPost.target_channels)
        )
        for row in scheduled_result:
            group_msg_ids, is_published, target_channels = row
            if not is_published:
                continue
            if group_msg_ids:
                try:
                    group_ids = json.loads(group_msg_ids) if isinstance(group_msg_ids, str) else group_msg_ids
                    if chat_id_str in group_ids:
                        count += 1
                        continue
                except:
                    pass
            if target_channels:
                try:
                    targets = json.loads(target_channels) if isinstance(target_channels, str) else target_channels
                    if chat_id in targets or chat_id_str in [str(t) for t in targets]:
                        count += 1
                        continue
                except:
                    pass
        
        # 3. Count from Study Plans (published to channel)
        channel_result = await session.execute(
            select(ChannelGroup.chat_id).where(ChannelGroup.type == 'channel', ChannelGroup.is_active == True).limit(1)
        )
        channel_chat_id = channel_result.scalar_one_or_none()
        channel_chat_id_str = str(channel_chat_id) if channel_chat_id else None
        
        plans_result = await session.execute(
            select(StudyPlan.channel_message_id, StudyPlan.is_active, StudyPlan.target_channels)
        )
        for row in plans_result:
            channel_msg_id, is_active, target_channels = row
            if not is_active:
                continue
            if target_channels:
                try:
                    targets = json.loads(target_channels) if isinstance(target_channels, str) else target_channels
                    if chat_id in targets or chat_id_str in [str(t) for t in targets]:
                        count += 1
                        continue
                except:
                    pass
            if channel_msg_id and channel_chat_id_str and channel_chat_id_str == chat_id_str:
                count += 1
        
        return count

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
async def get_channel_groups():
    groups = await get_all_channel_groups()
    result = []
    for g in groups:
        post_count = await count_posts_for_chat(g.chat_id)
        result.append({
            "id": g.id,
            "chatId": g.chat_id,
            "title": g.title,
            "type": g.type,
            "memberCount": g.member_count,
            "inviteLink": g.invite_link,
            "isActive": g.is_active,
            "isOfficial": g.is_official,
            "postCount": post_count,
            "createdAt": g.created_at.isoformat() if g.created_at else None
        })
    return result

@router.get("/active")
async def get_active_channel_groups_endpoint():
    groups = await get_active_channel_groups()
    result = []
    for g in groups:
        post_count = await count_posts_for_chat(g.chat_id)
        result.append({
            "id": g.id,
            "chatId": g.chat_id,
            "title": g.title,
            "type": g.type,
            "memberCount": g.member_count,
            "inviteLink": g.invite_link,
            "isActive": g.is_active,
            "postCount": post_count,
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
