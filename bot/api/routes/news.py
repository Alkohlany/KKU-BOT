from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bot.services.database import async_session, add_news, get_all_news, publish_news, delete_news, add_auto_response, add_question, update_news, delete_all_news, get_news_by_id
from bot.services.news_publisher import publish_to_groups, delete_from_channel, delete_from_groups, edit_published_messages
from bot.services.cloud_storage import upload_image

from bot.models.models import News
from bot.config import BOT_TOKEN
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
    content: str
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    as_document: bool = False
    file_id: Optional[str] = None
    target_channels: Optional[str] = None
    files_json: Optional[str] = None


class NewsAnalyze(BaseModel):
    title: str
    content: str


class RelinkPayload(BaseModel):
    keywords: list[str] = []
    questions: list[str] = []


@router.get("/")
async def get_news():
    items = await get_all_news()
    return [
        {
            "id": n.id,
            "content": n.content,
            "imageUrl": n.image_url,
            "fileUrl": n.file_url,
            "thumbnailUrl": n.thumbnail_url,
            "fileName": n.file_name,
            "fileId": n.file_id,
            "fileType": n.file_type,
            "published": n.is_published,
            "asDocument": n.as_document,
            "channelMessageId": n.channel_message_id,
            "targetChannels": n.target_channels,
            "filesJson": n.files_json,
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
    n = await add_news(content=data.content,
                         image_url=data.image_url, file_url=data.file_url,
                         file_name=data.file_name,
                         as_document=data.as_document,
                         file_id=data.file_id,
                         target_channels=data.target_channels,
                         files_json=data.files_json)
    return {"id": n.id, "content": n.content,
            "imageUrl": n.image_url, "fileUrl": n.file_url, "fileName": n.file_name, "fileId": n.file_id,
            "published": n.is_published,
            "as_document": n.as_document}


@router.post("/upload")
async def create_news_with_file(
    content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    files: list[UploadFile] = File(default=[]),
    as_document: bool = Form(False),
    target_channels: Optional[str] = Form(None),
    selected_keywords: str = Form("[]"),
    selected_questions: str = Form("[]"),
):
    try:
        import json

        files_list = files or ([file] if file else [])
        files_json_data = []

        image_url = None
        file_url = None
        thumbnail_url = None
        file_type = None

        if files_list:
            for f in files_list:
                file_data = await f.read()
                ext = f.filename.lower().split('.')[-1] if '.' in f.filename else ''
                ft = detect_file_type(f.filename)
                local_url = None
                remote_url = None

                if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                    if as_document:
                        local_url = save_file_locally(file_data, f.filename)
                    else:
                        try:
                            remote_url = upload_image(file_data, folder="kku-bot/news")
                        except Exception as e:
                            raise HTTPException(status_code=500, detail=f"فشل رفع الصورة لـ Cloudinary: {str(e)}")
                else:
                    local_url = save_file_locally(file_data, f.filename)

                thumb = None
                if ext == 'pdf' and local_url:
                    thumb = generate_pdf_thumbnail(local_url)

                url = remote_url or local_url
                files_json_data.append({
                    "url": url,
                    "type": ft,
                    "name": f.filename,
                    "thumbnail": thumb,
                })

            first = files_list[0]
            first_ext = first.filename.lower().split('.')[-1] if '.' in first.filename else ''
            file_type = detect_file_type(first.filename)
            if first_ext in ('jpg', 'jpeg', 'png', 'gif', 'webp') and not as_document:
                image_url = files_json_data[0]["url"]
            else:
                file_url = files_json_data[0]["url"]
            thumbnail_url = files_json_data[0].get("thumbnail")

        n = await add_news(content=content, image_url=image_url, file_url=file_url, thumbnail_url=thumbnail_url, file_name=files_list[0].filename if files_list else None, file_type=file_type,
                            as_document=as_document, target_channels=target_channels,
                            files_json=json.dumps(files_json_data) if files_json_data else None)

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

        return {"id": n.id, "content": n.content,
                "imageUrl": n.image_url, "fileUrl": n.file_url, "fileName": n.file_name, "fileId": n.file_id,
                "published": n.is_published,
                "asDocument": n.as_document,
                "filesJson": n.files_json}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ غير متوقع: {str(e)}")


@router.post("/{news_id}/publish")
async def publish_news_endpoint(news_id: int):
    async with async_session() as session:
        from sqlalchemy import select as sa_select
        result = await session.execute(sa_select(News).where(News.id == news_id))
        news = result.scalar_one_or_none()
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        as_document = news.as_document
        text = news.content
        sent, channel_message_id, group_message_ids = await publish_to_groups(text=text, image_url=news.image_url, file_url=news.file_url, file_id=news.file_id,
                                        as_document=as_document,
                                        file_name=news.file_name, thumbnail_url=news.thumbnail_url,
                                        target_channels=news.target_channels,
                                        files_json=news.files_json)

        await publish_news(news_id)
        import json
        if channel_message_id or group_message_ids:
            from bot.services.database import update_news
            await update_news(news_id, channel_message_id=channel_message_id, group_message_ids=json.dumps(group_message_ids) if group_message_ids else None)
        return {"status": "published", "sent": sent, "failed": 0}


@router.delete("/{news_id}")
async def delete_news_endpoint(news_id: int):
    import json
    n = await get_news_by_id(news_id)
    if n:
        if n.group_message_ids:
            try:
                await delete_from_groups(n.group_message_ids)
            except:
                pass
        if n.channel_message_id:
            try:
                await delete_from_channel(n.channel_message_id)
            except:
                pass
    await delete_news(news_id)
    return {"status": "deleted"}


@router.put("/{news_id}")
async def edit_news(news_id: int, data: NewsCreate):
    import json
    n = await get_news_by_id(news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    
    # Update the news in database
    await update_news(news_id, content=data.content,
                          image_url=data.image_url, file_url=data.file_url,
                          as_document=data.as_document,
                          target_channels=data.target_channels)
    
    # Fetch updated news
    updated = await get_news_by_id(news_id)
    
    # Edit published messages in groups and channel
    edited_count = 0
    failed_count = 0
    
    # Parse group_message_ids
    group_message_ids = {}
    if n.group_message_ids:
        try:
            group_message_ids = json.loads(n.group_message_ids)
        except:
            pass
    
    if group_message_ids or n.channel_message_id:
        text = data.content
        edited_count, failed_count = await edit_published_messages(
            text=text,
            group_message_ids=group_message_ids,
            channel_message_id=n.channel_message_id,
            image_url=data.image_url or n.image_url,
            file_url=data.file_url or n.file_url,
            as_document=data.as_document,
            file_name=n.file_name
        )
    
    return {"id": updated.id, "content": updated.content,
            "imageUrl": updated.image_url, "fileUrl": updated.file_url,
            "asDocument": updated.as_document, "channelMessageId": updated.channel_message_id,
            "targetChannels": updated.target_channels,
            "editedMessages": edited_count, "failedMessages": failed_count}


@router.put("/{news_id}/upload")
async def edit_news_with_file(
    news_id: int,
    content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    files: list[UploadFile] = File(default=[]),
    as_document: bool = Form(False),
    target_channels: Optional[str] = Form(None),
):
    import json

    existing = await get_news_by_id(news_id)
    if not existing:
        raise HTTPException(status_code=404, detail="News not found")

    files_list = files or ([file] if file else [])
    files_json_data = []

    image_url = None
    file_url = None
    file_name = None
    file_type = None
    thumbnail_url = None

    if files_list:
        for f in files_list:
            file_data = await f.read()
            ext = f.filename.lower().split('.')[-1] if '.' in f.filename else ''
            ft = detect_file_type(f.filename)
            local_url = None
            remote_url = None

            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                if as_document:
                    local_url = save_file_locally(file_data, f.filename)
                else:
                    try:
                        remote_url = upload_image(file_data, folder="kku-bot/news")
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"فشل رفع الصورة لـ Cloudinary: {str(e)}")
            else:
                local_url = save_file_locally(file_data, f.filename)

            thumb = None
            if ext == 'pdf' and local_url:
                thumb = generate_pdf_thumbnail(local_url)

            url = remote_url or local_url
            files_json_data.append({
                "url": url,
                "type": ft,
                "name": f.filename,
                "thumbnail": thumb,
            })

        first = files_list[0]
        first_ext = first.filename.lower().split('.')[-1] if '.' in first.filename else ''
        file_type = detect_file_type(first.filename)
        if first_ext in ('jpg', 'jpeg', 'png', 'gif', 'webp') and not as_document:
            image_url = files_json_data[0]["url"]
        else:
            file_url = files_json_data[0]["url"]
        file_name = first.filename
        thumbnail_url = files_json_data[0].get("thumbnail")

    await update_news(news_id, content=content,
                      image_url=image_url, file_url=file_url,
                      file_name=file_name, file_type=file_type,
                      thumbnail_url=thumbnail_url,
                      as_document=as_document, target_channels=target_channels,
                      files_json=json.dumps(files_json_data) if files_json_data else None)

    updated = await get_news_by_id(news_id)

    group_message_ids = {}
    if existing.group_message_ids:
        try:
            group_message_ids = json.loads(existing.group_message_ids)
        except:
            pass

    edited_count = 0
    failed_count = 0
    if group_message_ids or existing.channel_message_id:
        edited_count, failed_count = await edit_published_messages(
            text=content,
            group_message_ids=group_message_ids,
            channel_message_id=existing.channel_message_id,
            image_url=image_url or existing.image_url,
            file_url=file_url or existing.file_url,
            as_document=as_document,
            file_name=file_name or existing.file_name
        )

    return {"id": updated.id, "content": updated.content,
            "imageUrl": updated.image_url, "fileUrl": updated.file_url,
            "fileName": updated.file_name, "fileType": updated.file_type,
            "thumbnailUrl": updated.thumbnail_url,
            "asDocument": updated.as_document,
            "filesJson": updated.files_json,
            "editedMessages": edited_count, "failedMessages": failed_count}


@router.delete("/{news_id}/channel")
async def delete_from_channel_endpoint(news_id: int):
    n = await get_news_by_id(news_id)
    if n.channel_message_id:
        await delete_from_channel(n.channel_message_id)
        await update_news(news_id, channel_message_id=None, is_published=False)
    elif n.group_message_ids:
        await delete_from_groups(n.group_message_ids)
        await update_news(news_id, group_message_ids=None, is_published=False)
    return {"status": "deleted_from_channel"}


@router.delete("/")
async def delete_all_news_endpoint():
    import json
    items = await get_all_news()
    for item in items:
        if item.group_message_ids:
            try:
                group_ids = json.loads(item.group_message_ids)
                await delete_from_groups(group_ids)
            except:
                pass
        if item.channel_message_id:
            try:
                await delete_from_channel(item.channel_message_id)
            except:
                pass
    await delete_all_news()
    return {"status": "deleted_all"}


@router.post("/{news_id}/relink")
async def relink_news(news_id: int, data: RelinkPayload):
    n = await get_news_by_id(news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    async with async_session() as session:
        from sqlalchemy import delete as sa_delete
        from bot.models.models import AutoResponse, Question
        await session.execute(sa_delete(AutoResponse).where(AutoResponse.news_id == news_id))
        await session.execute(sa_delete(Question).where(Question.news_id == news_id))
        await session.commit()
    for kw in data.keywords:
        if kw and kw.strip() and len(kw.strip()) >= 2:
            await add_auto_response(keyword=kw.strip(), response=f"رد تلقائي لكلمة: {kw}", created_by=None, news_id=news_id)
    for q in data.questions:
        if q and q.strip() and len(q.strip()) >= 2:
            await add_question(question=q.strip(), answer=f"إجابة لكلمة: {q}", news_id=news_id)
    return {"status": "relinked", "keywords": len(data.keywords), "questions": len(data.questions)}


class EnhanceRequest(BaseModel):
    title: str = ""
    content: str = ""


@router.post("/enhance")
async def enhance_content_endpoint(request: EnhanceRequest):
    try:
        from bot.services.ai import enhance_content
        result = enhance_content(
            title=request.title,
            content=request.content
        )
        return {"enhanced": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل تحسين المحتوى: {str(e)}")
