from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bot.services.database import async_session, add_news, get_all_news, publish_news, get_all_groups, delete_news
from bot.services.news_publisher import publish_to_groups
from bot.services.cloud_storage import upload_image, upload_raw
from bot.models.models import News
from bot.config import BOT_TOKEN
import httpx

router = APIRouter()


def detect_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'photo'
    if ext in ('mp4', 'avi', 'mov', 'mkv'):
        return 'video'
    return 'document'


class NewsCreate(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    publish_to_channel: bool = False
    as_document: bool = False


class PublishPayload(BaseModel):
    publish_to_channel: bool = False
    as_document: bool = False


@router.get("/")
async def get_news():
    items = await get_all_news()
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "imageUrl": n.image_url,
            "fileUrl": n.file_url,
            "fileName": n.file_name,
            "published": n.is_published,
            "publishToChannel": n.publish_to_channel,
            "asDocument": n.as_document,
            "publishedAt": n.published_at.isoformat() if n.published_at else None,
            "createdAt": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.post("/")
async def create_news(data: NewsCreate):
    n = await add_news(title=data.title, content=data.content,
                         image_url=data.image_url, file_url=data.file_url,
                         file_name=data.file_name,
                         publish_to_channel=data.publish_to_channel,
                         as_document=data.as_document)
    return {"id": n.id, "title": n.title, "content": n.content,
            "imageUrl": n.image_url, "fileUrl": n.file_url, "fileName": n.file_name,
            "published": n.is_published,
            "publishToChannel": n.publish_to_channel, "as_document": n.as_document}


@router.post("/upload")
async def create_news_with_file(
    title: str = Form(...),
    content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    publish_to_channel: bool = Form(False),
    as_document: bool = Form(False),
):
    image_url = None
    file_url = None
    file_type = None

    if file:
        ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            img_data = await file.read()
            url = upload_image(img_data, folder="kku-bot/news")
            file_type = detect_file_type(file.filename)
            if as_document:
                file_url = url
            else:
                image_url = url
        else:
            file_data = await file.read()
            file_url = upload_raw(file_data, filename=file.filename, folder="kku-bot/news")
            file_type = detect_file_type(file.filename)

    n = await add_news(title=title, content=content, image_url=image_url, file_url=file_url, file_name=file.filename if file and file.filename else None, file_type=file_type,
                        publish_to_channel=publish_to_channel, as_document=as_document)
    return {"id": n.id, "title": n.title, "content": n.content,
            "imageUrl": n.image_url, "fileUrl": n.file_url, "fileName": n.file_name, "published": n.is_published,
            "publishToChannel": n.publish_to_channel, "asDocument": n.as_document}


@router.post("/{news_id}/publish")
async def publish_news_endpoint(news_id: int, payload: PublishPayload = None):
    async with async_session() as session:
        from sqlalchemy import select as sa_select
        result = await session.execute(sa_select(News).where(News.id == news_id))
        news = result.scalar_one_or_none()
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        publish_to_channel = payload.publish_to_channel if payload else news.publish_to_channel
        as_document = payload.as_document if payload else news.as_document
        text = f"📰 {news.title}\n\n{news.content}"
        sent = await publish_to_groups(text=text, image_url=news.image_url, file_url=news.file_url,
                                        publish_to_channel=publish_to_channel, as_document=as_document,
                                        file_name=news.file_name)

        await publish_news(news_id)
        return {"status": "published", "sent": sent, "failed": 0}


@router.delete("/{news_id}")
async def delete_news_endpoint(news_id: int):
    await delete_news(news_id)
    return {"status": "deleted"}
