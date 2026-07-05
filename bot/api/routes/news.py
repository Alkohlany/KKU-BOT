from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bot.services.database import add_news, get_all_news, publish_news, get_all_groups, delete_news
from bot.services.news_publisher import publish_to_groups
from bot.services.cloud_storage import upload_image, upload_raw
from bot.models.models import News
from bot.config import BOT_TOKEN
import httpx

router = APIRouter()


class NewsCreate(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    file_url: Optional[str] = None


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
            "published": n.is_published,
            "publishedAt": n.published_at.isoformat() if n.published_at else None,
            "createdAt": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.post("/")
async def create_news(data: NewsCreate):
    n = await add_news(title=data.title, content=data.content,
                         image_url=data.image_url, file_url=data.file_url)
    return {"id": n.id, "title": n.title, "content": n.content,
            "imageUrl": n.image_url, "fileUrl": n.file_url, "published": n.is_published}


@router.post("/upload")
async def create_news_with_file(
    title: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
):
    image_url = None
    file_url = None

    if image:
        img_data = await image.read()
        image_url = upload_image(img_data, folder="kku-bot/news")

    if file:
        file_data = await file.read()
        file_url = upload_raw(file_data, filename=file.filename, folder="kku-bot/news")

    n = await add_news(title=title, content=content, image_url=image_url, file_url=file_url)
    return {"id": n.id, "title": n.title, "content": n.content,
            "imageUrl": n.image_url, "fileUrl": n.file_url, "published": n.is_published}


@router.post("/{news_id}/publish")
async def publish_news_endpoint(news_id: int):
    async with __import__('bot.services.database', fromlist=['async_session']).async_session() as session:
        from sqlalchemy import select as sa_select
        result = await session.execute(sa_select(News).where(News.id == news_id))
        news = result.scalar_one_or_none()
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        text = f"📰 {news.title}\n\n{news.content}"
        sent = await publish_to_groups(text=text, image_url=news.image_url, file_url=news.file_url)

        await publish_news(news_id)
        return {"status": "published", "sent": sent, "failed": 0}


@router.delete("/{news_id}")
async def delete_news_endpoint(news_id: int):
    await delete_news(news_id)
    return {"status": "deleted"}
