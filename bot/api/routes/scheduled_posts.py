from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from bot.services.database import (add_scheduled_post, get_all_scheduled_posts, 
                                   get_pending_posts, mark_post_published, delete_scheduled_post)
from bot.services.cloud_storage import upload_image, upload_raw

router = APIRouter()


class ScheduledPostCreate(BaseModel):
    title: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    schedule_time: datetime
    is_recurring: bool = False
    recurring_interval: Optional[str] = None


@router.get("/")
async def get_scheduled_posts():
    items = await get_all_scheduled_posts()
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "imageUrl": p.image_url,
            "fileUrl": p.file_url,
            "scheduledTime": p.schedule_time.isoformat() if p.schedule_time else None,
            "recurring": p.is_recurring,
            "recurringInterval": p.recurring_interval,
            "isPublished": p.is_published,
            "createdAt": p.created_at.isoformat() if p.created_at else None,
        }
        for p in items
    ]


@router.post("/")
async def create_scheduled_post(data: ScheduledPostCreate):
    dt = data.schedule_time
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        riyadh_tz = ZoneInfo("Asia/Riyadh")
        dt = dt.replace(tzinfo=riyadh_tz).astimezone(timezone.utc).replace(tzinfo=None)
    p = await add_scheduled_post(title=data.title, content=data.content,
                                   schedule_time=dt,
                                   image_url=data.image_url, file_url=data.file_url,
                                   is_recurring=data.is_recurring,
                                   recurring_interval=data.recurring_interval)
    return {
        "id": p.id, "title": p.title, "content": p.content,
        "imageUrl": p.image_url, "fileUrl": p.file_url,
        "scheduledTime": p.schedule_time.isoformat() if p.schedule_time else None,
        "recurring": p.is_recurring, "isPublished": p.is_published
    }


@router.post("/upload")
async def create_scheduled_post_with_file(
    content: str = Form(...),
    schedule_time: str = Form(...),
    is_recurring: bool = Form(False),
    title: Optional[str] = Form(None),
    recurring_interval: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
):
    image_url = None
    file_url = None

    if image:
        img_data = await image.read()
        image_url = upload_image(img_data, folder="kku-bot/scheduled")

    if file:
        file_data = await file.read()
        file_url = upload_raw(file_data, filename=file.filename, folder="kku-bot/scheduled")

    dt = datetime.fromisoformat(schedule_time)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        riyadh_tz = ZoneInfo("Asia/Riyadh")
        dt = dt.replace(tzinfo=riyadh_tz).astimezone(timezone.utc).replace(tzinfo=None)
    p = await add_scheduled_post(title=title, content=content,
                                   schedule_time=dt,
                                   image_url=image_url, file_url=file_url,
                                   is_recurring=is_recurring,
                                   recurring_interval=recurring_interval)
    return {
        "id": p.id, "title": p.title, "content": p.content,
        "imageUrl": p.image_url, "fileUrl": p.file_url,
        "scheduledTime": p.schedule_time.isoformat() if p.schedule_time else None,
        "recurring": p.is_recurring, "isPublished": p.is_published
    }


@router.delete("/{post_id}")
async def delete_scheduled_post_endpoint(post_id: int):
    await delete_scheduled_post(post_id)
    return {"status": "deleted"}
