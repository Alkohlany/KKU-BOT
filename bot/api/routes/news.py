from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bot.services.database import async_session, add_news, get_all_news, publish_news, get_all_groups, delete_news, add_auto_response, add_question
from bot.services.news_publisher import publish_to_groups
from bot.services.cloud_storage import upload_image
from bot.models.models import News
from bot.config import BOT_TOKEN, CHANNEL_ID
import os
import uuid

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'news')


def generate_pdf_thumbnail(pdf_path: str) -> str | None:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return None
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        thumb_path = pdf_path.rsplit('.', 1)[0] + '_thumb.jpg'
        pix.save(thumb_path)
        doc.close()
        return thumb_path
    except Exception as e:
        return None


def save_file_locally(file_data: bytes, filename: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return file_path


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
    file_id: Optional[str] = None


class NewsAnalyze(BaseModel):
    title: str
    content: str


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
            "thumbnailUrl": n.thumbnail_url,
            "fileName": n.file_name,
            "fileId": n.file_id,
            "fileType": n.file_type,
            "published": n.is_published,
            "publishToChannel": n.publish_to_channel,
            "asDocument": n.as_document,
            "publishedAt": n.published_at.isoformat() if n.published_at else None,
            "createdAt": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.post("/analyze")
async def analyze_news(data: NewsAnalyze):
    try:
        from bot.services.ai import generate_news_analysis
        result = generate_news_analysis(data.title, data.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل تحليل المحتوى: {str(e)}")


@router.post("/")
async def create_news(data: NewsCreate):
    n = await add_news(title=data.title, content=data.content,
                         image_url=data.image_url, file_url=data.file_url,
                         file_name=data.file_name,
                         publish_to_channel=data.publish_to_channel,
                         as_document=data.as_document,
                         file_id=data.file_id)
    return {"id": n.id, "title": n.title, "content": n.content,
            "imageUrl": n.image_url, "fileUrl": n.file_url, "fileName": n.file_name, "fileId": n.file_id,
            "published": n.is_published,
            "publishToChannel": n.publish_to_channel, "as_document": n.as_document}


@router.post("/upload")
async def create_news_with_file(
    title: str = Form(...),
    content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    publish_to_channel: bool = Form(False),
    as_document: bool = Form(False),
    selected_keywords: str = Form("[]"),
    selected_questions: str = Form("[]"),
):
    try:
        image_url = None
        file_url = None
        thumbnail_url = None
        file_type = None

        if file:
            file_data = await file.read()
            ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                file_type = detect_file_type(file.filename)
                if as_document:
                    file_url = save_file_locally(file_data, file.filename)
                else:
                    try:
                        url = upload_image(file_data, folder="kku-bot/news")
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"فشل رفع الصورة لـ Cloudinary: {str(e)}")
                    image_url = url
            else:
                file_url = save_file_locally(file_data, file.filename)
                file_type = detect_file_type(file.filename)
                if ext == 'pdf':
                    thumbnail_url = generate_pdf_thumbnail(file_url)

        n = await add_news(title=title, content=content, image_url=image_url, file_url=file_url, thumbnail_url=thumbnail_url, file_name=file.filename if file and file.filename else None, file_type=file_type,
                            publish_to_channel=publish_to_channel, as_document=as_document)

        import json
        try:
            keywords = json.loads(selected_keywords) if selected_keywords else []
        except:
            keywords = []
        try:
            questions = json.loads(selected_questions) if selected_questions else []
        except:
            questions = []

        def is_valid_item(item: str) -> bool:
            if not item or not item.strip():
                return False
            item = item.strip()
            if len(item) < 2:
                return False
            if item.startswith('#') or item.startswith('http') or item.startswith('t.me'):
                return False
            if 't.me/' in item or 'http' in item.lower():
                return False
            return True

        for kw in keywords:
            if is_valid_item(kw):
                await add_auto_response(keyword=kw.strip(), response=f"رد تلقائي لكلمة: {kw}", created_by=None, news_id=n.id)

        for q in questions:
            if is_valid_item(q):
                await add_question(question=q.strip(), answer=f"إجابة لكلمة: {q}", news_id=n.id)

        text = f"📰 {title}\n\n{content}"
        sent = await publish_to_groups(text=text, image_url=image_url, file_url=file_url,
                                        publish_to_channel=publish_to_channel, as_document=as_document,
                                        file_name=file.filename if file and file.filename else None,
                                        thumbnail_url=thumbnail_url)
        await publish_news(n.id)

        return {"id": n.id, "title": n.title, "content": n.content,
                "imageUrl": n.image_url, "fileUrl": n.file_url, "fileName": n.file_name, "fileId": n.file_id,
                "published": True, "sent": sent,
                "publishToChannel": n.publish_to_channel, "asDocument": n.as_document}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ غير متوقع: {str(e)}")


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
        sent = await publish_to_groups(text=text, image_url=news.image_url, file_url=news.file_url, file_id=news.file_id,
                                        publish_to_channel=publish_to_channel, as_document=as_document,
                                        file_name=news.file_name, thumbnail_url=news.thumbnail_url)

        await publish_news(news_id)
        return {"status": "published", "sent": sent, "failed": 0}


@router.delete("/{news_id}")
async def delete_news_endpoint(news_id: int):
    await delete_news(news_id)
    return {"status": "deleted"}
