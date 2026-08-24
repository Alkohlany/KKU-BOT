from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bot.services.database import async_session, add_news, get_all_news, publish_news, delete_news, add_auto_response, add_question, update_news, delete_all_news, get_news_by_id, update_auto_response
from bot.services.news_publisher import publish_to_groups, delete_from_channel, delete_from_groups, edit_published_messages, resend_published_messages
from bot.services.cloud_storage import upload_image, upload_raw, find_file_by_name, find_file_by_content

from bot.models.models import News
from bot.config import BOT_TOKEN
import os
import uuid
import tempfile

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'news')


def generate_pdf_thumbnail(pdf_path: str) -> str | None:
    try:
        import fitz
        from PIL import Image
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return None
        page = doc[0]
        mat = fitz.Matrix(1.0, 1.0)
        pix = page.get_pixmap(matrix=mat)
        thumb_path = pdf_path.rsplit('.', 1)[0] + '_thumb.jpg'
        pix.save(thumb_path)
        doc.close()
        img = Image.open(thumb_path)
        img.thumbnail((320, 320), Image.LANCZOS)
        img.save(thumb_path, "JPEG", quality=85)
        return thumb_path
    except Exception as e:
        return None


def upload_to_cloud(file_data: bytes, filename: str, folder: str = "kku-bot/news") -> tuple[str, str | None]:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    thumb_url = None
    tmp_path = None
    thumb_tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        if ext == 'pdf':
            thumb_tmp = generate_pdf_thumbnail(tmp_path)
        main_url = upload_raw(file_data, filename=filename, folder=folder)
        if thumb_tmp and os.path.exists(thumb_tmp):
            with open(thumb_tmp, 'rb') as f:
                thumb_data = f.read()
            thumb_url = upload_raw(thumb_data, filename="thumb.jpg", folder=folder)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if thumb_tmp and os.path.exists(thumb_tmp):
            os.unlink(thumb_tmp)
    return main_url, thumb_url


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
    as_document: Optional[bool] = None
    file_id: Optional[str] = None
    target_channels: Optional[str] = None
    files_json: Optional[str] = None
    removed_existing: Optional[str] = None
    selected_keywords: Optional[str] = None
    selected_questions: Optional[str] = None
    linked_response_id: Optional[str] = None


class NewsAnalyze(BaseModel):
    title: str
    content: str


class RelinkPayload(BaseModel):
    keywords: list[str] = []
    questions: list[str] = []


@router.get("")
async def get_news(search: str = Query(None)):
    from sqlalchemy import select as sa_select, func as sa_func
    from sqlalchemy.orm import selectinload

    async with async_session() as session:
        stmt = (
            sa_select(News)
            .options(selectinload(News.auto_responses), selectinload(News.questions))
            .order_by(News.created_at.desc())
        )

        if search:
            stmt = stmt.where(News.content.ilike(f"%{search}%"))

        items = (await session.execute(stmt)).scalars().unique().all()

        result = []
        for n in items:
            keywords = [ar.keyword for ar in n.auto_responses]
            linked = next((ar.id for ar in n.auto_responses), None)
            questions = [q.question for q in n.questions]
            result.append({
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
                "selectedKeywords": keywords,
                "selectedQuestions": questions,
                "linked_response_id": linked,
            })
        return {"items": result, "total": len(result)}


@router.post("/analyze")
async def analyze_news(data: NewsAnalyze):
    try:
        from bot.services.ai import generate_news_analysis
        result = generate_news_analysis(data.title, data.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل تحليل المحتوى: {str(e)}")


@router.post("")
async def create_news(data: NewsCreate):
    import json
    n = await add_news(content=data.content,
                         image_url=data.image_url, file_url=data.file_url,
                         file_name=data.file_name,
                         as_document=data.as_document,
                         file_id=data.file_id,
                         target_channels=data.target_channels,
                         files_json=data.files_json)

    if data.selected_keywords:
        try:
            keywords = json.loads(data.selected_keywords)
        except:
            keywords = []
        for kw in keywords:
            if kw and kw.strip() and len(kw.strip()) >= 2 and not kw.startswith('#') and not kw.startswith('http'):
                await add_auto_response(keyword=kw.strip(), response=f"رد تلقائي لكلمة: {kw}", created_by=None, news_id=n.id)

    if data.selected_questions:
        try:
            questions = json.loads(data.selected_questions)
        except:
            questions = []
        for q in questions:
            if q and q.strip() and len(q.strip()) >= 2 and not q.startswith('#') and not q.startswith('http'):
                await add_question(question=q.strip(), answer=f"إجابة لكلمة: {q}", news_id=n.id)

    if data.linked_response_id:
        try:
            await update_auto_response(int(data.linked_response_id), news_id=n.id)
        except:
            pass

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
    file_captions: str = Form("{}"),
    linked_response_id: str = Form(""),
    cloud_files: str = Form("[]"),
):
    try:
        import json

        files_list = files or ([file] if file else [])
        files_json_data = []

        image_url = None
        file_url = None
        thumbnail_url = None
        file_type = None

        try:
            file_captions_dict = json.loads(file_captions) if file_captions else {}
        except:
            file_captions_dict = {}

        try:
            cloud_files_list = json.loads(cloud_files) if cloud_files else []
        except:
            cloud_files_list = []
        cloud_urls_map = {cf['index']: cf['url'] for cf in cloud_files_list}

        if files_list:
            for i, f in enumerate(files_list):
                if i in cloud_urls_map:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(cloud_urls_map[i])
                        file_data = resp.content
                else:
                    file_data = await f.read()
                ext = f.filename.lower().split('.')[-1] if '.' in f.filename else ''
                ft = detect_file_type(f.filename)
                remote_url = None
                thumb = None

                existing_url = find_file_by_name(f.filename, "kku-bot/news")
                if not existing_url:
                    existing_url = find_file_by_content(file_data, "kku-bot/news")
                if existing_url:
                    remote_url = existing_url
                elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                    if as_document:
                        remote_url = upload_raw(file_data, filename=f.filename, folder="kku-bot/news")
                    else:
                        try:
                            remote_url = upload_image(file_data, folder="kku-bot/news")
                        except Exception as e:
                            raise HTTPException(status_code=500, detail=f"فشل رفع الصورة للتخزين السحابي: {str(e)}")
                else:
                    remote_url, thumb = upload_to_cloud(file_data, f.filename, folder="kku-bot/news")

                files_json_data.append({
                    "url": remote_url,
                    "type": ft,
                    "name": f.filename,
                    "thumbnail": thumb,
                    "caption": file_captions_dict.get(str(i), ""),
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
                      files_json=json.dumps(files_json_data))

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

        if linked_response_id:
            try:
                await update_auto_response(int(linked_response_id), news_id=n.id)
            except:
                pass

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
    
    # Handle removed existing files
    if data.removed_existing:
        try:
            removed_indices = json.loads(data.removed_existing)
            if removed_indices and n.files_json:
                existing = json.loads(n.files_json) if isinstance(n.files_json, str) else (n.files_json or [])
                existing = [f for i, f in enumerate(existing) if i not in removed_indices]
                await update_news(news_id, files_json=json.dumps(existing))
        except:
            pass

    # Update the news in database
    await update_news(news_id, content=data.content,
                          image_url=data.image_url, file_url=data.file_url,
                          as_document=data.as_document,
                          target_channels=data.target_channels)

    if data.selected_keywords:
        try:
            keywords = json.loads(data.selected_keywords)
        except:
            keywords = []
        for kw in keywords:
            if kw and kw.strip() and len(kw.strip()) >= 2 and not kw.startswith('#') and not kw.startswith('http'):
                await add_auto_response(keyword=kw.strip(), response=f"رد تلقائي لكلمة: {kw}", created_by=None, news_id=n.id)

    if data.selected_questions:
        try:
            questions = json.loads(data.selected_questions)
        except:
            questions = []
        for q in questions:
            if q and q.strip() and len(q.strip()) >= 2 and not q.startswith('#') and not q.startswith('http'):
                await add_question(question=q.strip(), answer=f"إجابة لكلمة: {q}", news_id=n.id)

    if data.linked_response_id:
        try:
            await update_auto_response(int(data.linked_response_id), news_id=n.id)
        except:
            pass

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
    
    if n.is_published and (group_message_ids or n.channel_message_id):
        text = data.content
        edited_count, failed_count = await edit_published_messages(
            text=text,
            group_message_ids=group_message_ids,
            channel_message_id=n.channel_message_id,
            image_url=data.image_url or n.image_url,
            file_url=data.file_url or n.file_url,
            as_document=data.as_document if data.as_document is not None else n.as_document,
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
    removed_existing: Optional[str] = Form(None),
    file_captions: str = Form("{}"),
    selected_keywords: str = Form("[]"),
    selected_questions: str = Form("[]"),
    linked_response_id: str = Form(""),
    cloud_files: str = Form("[]"),
):
    import json

    existing = await get_news_by_id(news_id)
    if not existing:
        raise HTTPException(status_code=404, detail="News not found")

    files_list = files or ([file] if file else [])

    # Handle removed existing files - keep non-removed existing files
    try:
        file_captions_dict = json.loads(file_captions) if file_captions else {}
    except:
        file_captions_dict = {}

    try:
        cloud_files_list = json.loads(cloud_files) if cloud_files else []
    except:
        cloud_files_list = []
    cloud_urls_map = {cf['index']: cf['url'] for cf in cloud_files_list}

    kept_existing = []
    if removed_existing:
        try:
            removed_indices = json.loads(removed_existing)
            if existing.files_json:
                old_files = json.loads(existing.files_json) if isinstance(existing.files_json, str) else (existing.files_json or [])
                for i, f in enumerate(old_files):
                    if i not in removed_indices:
                        kept_existing.append((i, f))
        except:
            pass

    files_json_data = []
    for orig_idx, f in kept_existing:
        new_f = dict(f)
        if file_captions_dict:
            caption_key = str(orig_idx)
            if caption_key in file_captions_dict:
                new_f["caption"] = file_captions_dict[caption_key]
        files_json_data.append(new_f)

    image_url = None
    file_url = None
    file_name = None
    file_type = None
    thumbnail_url = None

    if files_list:
        for i, f in enumerate(files_list):
            if i in cloud_urls_map:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(cloud_urls_map[i])
                    file_data = resp.content
            else:
                file_data = await f.read()
            ext = f.filename.lower().split('.')[-1] if '.' in f.filename else ''
            ft = detect_file_type(f.filename)
            remote_url = None
            thumb = None

            existing_url = find_file_by_name(f.filename, "kku-bot/news")
            if not existing_url:
                existing_url = find_file_by_content(file_data, "kku-bot/news")
            if existing_url:
                remote_url = existing_url
            elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                if as_document:
                    remote_url = upload_raw(file_data, filename=f.filename, folder="kku-bot/news")
                else:
                    try:
                        remote_url = upload_image(file_data, folder="kku-bot/news")
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"فشل رفع الصورة للتخزين السحابي: {str(e)}")
            else:
                remote_url, thumb = upload_to_cloud(file_data, f.filename, folder="kku-bot/news")

            files_json_data.append({
                "url": remote_url,
                "type": ft,
                "name": f.filename,
                "thumbnail": thumb,
                "caption": file_captions_dict.get(str(i), ""),
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
                      files_json=json.dumps(files_json_data))

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
            await add_auto_response(keyword=kw.strip(), response=f"رد تلقائي لكلمة: {kw}", created_by=None, news_id=news_id)

    for q in questions:
        if is_valid_item(q):
            await add_question(question=q.strip(), answer=f"إجابة لكلمة: {q}", news_id=news_id)

    if linked_response_id:
        try:
            await update_auto_response(int(linked_response_id), news_id=news_id)
        except:
            pass

    updated = await get_news_by_id(news_id)

    group_message_ids = {}
    if existing.group_message_ids:
        try:
            group_message_ids = json.loads(existing.group_message_ids)
        except:
            pass

    edited_count = 0
    failed_count = 0
    new_group_ids = group_message_ids
    new_channel_id = existing.channel_message_id
    
    files_changed = bool(files_list)
    
    if existing.is_published and (group_message_ids or existing.channel_message_id):
        if files_changed:
            edited_count, failed_count, new_group_ids, new_channel_id = await resend_published_messages(
                text=content,
                group_message_ids=group_message_ids,
                channel_message_id=existing.channel_message_id,
                image_url=image_url,
                file_url=file_url,
                as_document=as_document,
                file_name=file_name,
                thumbnail_url=thumbnail_url,
                files_json=json.dumps(files_json_data) if files_json_data else None
            )
        else:
            edited_count, failed_count = await edit_published_messages(
                text=content,
                group_message_ids=group_message_ids,
                channel_message_id=existing.channel_message_id,
                image_url=image_url or existing.image_url,
                file_url=file_url or existing.file_url,
                as_document=as_document if as_document is not None else existing.as_document,
                file_name=file_name or existing.file_name
            )
    
    if files_changed and (new_group_ids != group_message_ids or new_channel_id != existing.channel_message_id):
        await update_news(news_id,
                         group_message_ids=json.dumps(new_group_ids) if new_group_ids else None,
                         channel_message_id=new_channel_id)

    return {"id": updated.id, "content": updated.content,
            "imageUrl": updated.image_url, "fileUrl": updated.file_url,
            "fileName": updated.file_name, "fileType": updated.file_type,
            "thumbnailUrl": updated.thumbnail_url,
            "asDocument": updated.as_document,
            "filesJson": updated.files_json,
            "editedMessages": edited_count, "failedMessages": failed_count}


@router.delete("/{news_id}/channel")
async def delete_from_channel_endpoint(news_id: int):
    import json
    n = await get_news_by_id(news_id)
    if not n:
        raise HTTPException(status_code=404, detail="News not found")
    # Delete from channel
    if n.channel_message_id:
        try:
            await delete_from_channel(n.channel_message_id)
        except:
            pass
    # Delete from groups
    if n.group_message_ids:
        try:
            group_ids = json.loads(n.group_message_ids) if isinstance(n.group_message_ids, str) else n.group_message_ids
            await delete_from_groups(group_ids)
        except:
            pass
    # Reset to draft
    await update_news(news_id, channel_message_id=None, group_message_ids=None, is_published=False)
    return {"status": "deleted_from_channel"}


@router.delete("")
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
