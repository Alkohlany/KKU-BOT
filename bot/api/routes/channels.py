from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from telegram import Bot
import os
from ...services.database import (
    get_all_channel_groups, get_active_channel_groups, 
    add_channel_group, toggle_channel_group, 
    update_channel_group, delete_channel_group,
    get_channel_group_by_chat_id
)

router = APIRouter()

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

@router.get("/")
async def get_channel_groups():
    groups = await get_all_channel_groups()
    return [
        {
            "id": g.id,
            "chatId": g.chat_id,
            "title": g.title,
            "type": g.type,
            "memberCount": g.member_count,
            "inviteLink": g.invite_link,
            "isActive": g.is_active,
            "createdAt": g.created_at.isoformat() if g.created_at else None
        }
        for g in groups
    ]

@router.get("/active")
async def get_active_channel_groups_endpoint():
    groups = await get_active_channel_groups()
    return [
        {
            "id": g.id,
            "chatId": g.chat_id,
            "title": g.title,
            "type": g.type,
            "memberCount": g.member_count,
            "inviteLink": g.invite_link,
            "isActive": g.is_active,
        }
        for g in groups
    ]

@router.post("/")
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
