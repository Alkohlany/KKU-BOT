from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from bot.services.database import (add_scheduled_post, get_all_scheduled_posts, 
                                   get_pending_posts, mark_post_published, delete_scheduled_post)
from bot.services.cloud_storage import upload_image, upload_raw
import os
import uuid
import tempfile

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'scheduled')


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


def upload_to_cloud(file_data: bytes, filename: str, folder: str = "kku-bot/scheduled") -> tuple[str, str | None]:
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


class ScheduledPostCreate(BaseModel):
    content: str
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    schedule_time: datetime
    is_recurring: bool = False
    recurring_interval: Optional[str] = None
    as_document: bool = False
    target_channels: Optional[str] = None
    files_json: Optional[str] = None
    removed_existing: Optional[str] = None


@router.get("")
async def get_scheduled_posts():
    items = await get_all_scheduled_posts()
    return [
        {
            "id": p.id,
            "content": p.content,
            "imageUrl": p.image_url,
            "fileUrl": p.file_url,
            "fileName": p.file_name,
            "fileType": p.file_type,
            "fileId": p.file_id,
            "thumbnailUrl": p.thumbnail_url,
            "scheduledTime": p.schedule_time.isoformat() if p.schedule_time else None,
            "recurring": p.is_recurring,
            "recurringInterval": p.recurring_interval,
            "isPublished": p.is_published,
            "asDocument": p.as_document,
            "targetChannels": p.target_channels,
            "filesJson": p.files_json,
            "createdAt": p.created_at.isoformat() if p.created_at else None,
        }
        for p in items
    ]


@router.post("")
async def create_scheduled_post(data: ScheduledPostCreate):
    dt = data.schedule_time
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        riyadh_tz = ZoneInfo("Asia/Riyadh")
        dt = dt.replace(tzinfo=riyadh_tz).astimezone(timezone.utc).replace(tzinfo=None)
    p = await add_scheduled_post(content=data.content,
                                    schedule_time=dt,
                                    image_url=data.image_url, file_url=data.file_url,
                                    file_name=data.file_name, file_type=data.file_type,
                                    file_id=data.file_id, thumbnail_url=data.thumbnail_url,
                                    is_recurring=data.is_recurring,
                                    recurring_interval=data.recurring_interval,
                                    as_document=data.as_document,
                                    target_channels=data.target_channels,
                                    files_json=data.files_json)
    return {
        "id": p.id, "content": p.content,
        "imageUrl": p.image_url, "fileUrl": p.file_url,
        "fileName": p.file_name, "fileType": p.file_type,
        "scheduledTime": p.schedule_time.isoformat() if p.schedule_time else None,
        "recurring": p.is_recurring, "isPublished": p.is_published,
        "asDocument": p.as_document, "filesJson": p.files_json
    }


@router.post("/upload")
async def create_scheduled_post_with_file(
    content: str = Form(...),
    schedule_time: str = Form(...),
    is_recurring: bool = Form(False),
    recurring_interval: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    files: list[UploadFile] = File(default=[]),
    as_document: bool = Form(False),
    target_channels: Optional[str] = Form(None),
):
    import json

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
            remote_url = None
            thumb = None

            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                if as_document:
                    remote_url = upload_raw(file_data, filename=f.filename, folder="kku-bot/scheduled")
                else:
                    remote_url = upload_image(file_data, folder="kku-bot/scheduled")
            else:
                remote_url, thumb = upload_to_cloud(file_data, f.filename, folder="kku-bot/scheduled")

            files_json_data.append({
                "url": remote_url,
                "type": ft,
                "name": f.filename,
                "thumbnail": thumb,
            })

        first = files_list[0]
        first_ext = first.filename.lower().split('.')[-1] if '.' in first.filename else ''
        file_type = detect_file_type(first.filename)
        file_url = files_json_data[0]["url"]
        file_name = first.filename
        thumbnail_url = files_json_data[0].get("thumbnail")

    dt = datetime.fromisoformat(schedule_time)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        riyadh_tz = ZoneInfo("Asia/Riyadh")
        dt = dt.replace(tzinfo=riyadh_tz).astimezone(timezone.utc).replace(tzinfo=None)
    p = await add_scheduled_post(content=content,
                                    schedule_time=dt,
                                    image_url=image_url, file_url=file_url,
                                    file_name=file_name, file_type=file_type,
                                    is_recurring=is_recurring,
                                    recurring_interval=recurring_interval,
                                    as_document=as_document,
                                    target_channels=target_channels,
                                    files_json=json.dumps(files_json_data) if files_json_data else None)
    return {
        "id": p.id, "content": p.content,
        "imageUrl": p.image_url, "fileUrl": p.file_url,
        "fileName": p.file_name, "fileType": p.file_type,
        "scheduledTime": p.schedule_time.isoformat() if p.schedule_time else None,
        "recurring": p.is_recurring, "isPublished": p.is_published,
        "asDocument": p.as_document, "filesJson": p.files_json
    }


@router.put("/{post_id}/upload")
async def update_scheduled_post_with_file(
    post_id: int,
    content: str = Form(...),
    schedule_time: str = Form(...),
    is_recurring: bool = Form(False),
    recurring_interval: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    files: list[UploadFile] = File(default=[]),
    as_document: bool = Form(False),
    target_channels: Optional[str] = Form(None),
    removed_existing: Optional[str] = Form(None),
):
    from ...services.database import get_scheduled_post, update_scheduled_post as update_post
    import json

    existing = await get_scheduled_post(post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if existing.is_published:
        raise HTTPException(status_code=400, detail="Cannot edit a published post")

    files_list = files or ([file] if file else [])

    # Handle removed existing files - keep non-removed existing files
    kept_existing = []
    if removed_existing:
        try:
            removed_indices = json.loads(removed_existing)
            if existing.files_json:
                old_files = json.loads(existing.files_json) if isinstance(existing.files_json, str) else (existing.files_json or [])
                kept_existing = [f for i, f in enumerate(old_files) if i not in removed_indices]
        except:
            pass

    files_json_data = list(kept_existing)

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
            remote_url = None
            thumb = None

            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                remote_url = upload_image(file_data, folder="kku-bot/scheduled")
            else:
                remote_url, thumb = upload_to_cloud(file_data, f.filename, folder="kku-bot/scheduled")

            files_json_data.append({
                "url": remote_url,
                "type": ft,
                "name": f.filename,
                "thumbnail": thumb,
            })

        first = files_list[0]
        file_type = detect_file_type(first.filename)
        file_url = files_json_data[0]["url"]
        file_name = first.filename
        thumbnail_url = files_json_data[0].get("thumbnail")

    dt = datetime.fromisoformat(schedule_time)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        riyadh_tz = ZoneInfo("Asia/Riyadh")
        dt = dt.replace(tzinfo=riyadh_tz).astimezone(timezone.utc).replace(tzinfo=None)

    updated = await update_post(
        post_id, content=content, schedule_time=dt,
        is_recurring=is_recurring, recurring_interval=recurring_interval,
        as_document=as_document, target_channels=target_channels,
        file_url=file_url, file_name=file_name, file_type=file_type,
        thumbnail_url=thumbnail_url,
        files_json=json.dumps(files_json_data) if files_json_data else existing.files_json,
    )
    return updated


@router.delete("/{post_id}/channel")
async def reset_post_publish(post_id: int):
    from ...services.database import get_scheduled_post
    from sqlalchemy import update
    from ...models.models import ScheduledPost
    from ...services.database import async_session

    existing = await get_scheduled_post(post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    async with async_session() as session:
        await session.execute(
            update(ScheduledPost)
            .where(ScheduledPost.id == post_id)
            .values(is_published=False, target_channels=None)
        )
        await session.commit()

    return {"status": "reset"}


@router.delete("/{post_id}")
async def delete_scheduled_post_endpoint(post_id: int):
    await delete_scheduled_post(post_id)
    return {"status": "deleted"}


@router.put("/{post_id}")
async def update_scheduled_post(post_id: int, post: ScheduledPostCreate):
    from ...services.database import get_scheduled_post, update_scheduled_post as update_post
    existing = await get_scheduled_post(post_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if existing.is_published:
        raise HTTPException(status_code=400, detail="Cannot edit a published post")
    dt = post.schedule_time
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        riyadh_tz = ZoneInfo("Asia/Riyadh")
        dt = dt.replace(tzinfo=riyadh_tz).astimezone(timezone.utc).replace(tzinfo=None)
    # Handle removed existing files
    if post.removed_existing:
        try:
            import json
            removed_indices = json.loads(post.removed_existing)
            if removed_indices and existing.files_json:
                old_files = json.loads(existing.files_json) if isinstance(existing.files_json, str) else (existing.files_json or [])
                kept = [f for i, f in enumerate(old_files) if i not in removed_indices]
                await update_post(post_id, files_json=json.dumps(kept) if kept else None)
        except:
            pass

    updated = await update_post(post_id, content=post.content, schedule_time=dt, is_recurring=post.is_recurring, recurring_interval=post.recurring_interval, as_document=post.as_document, target_channels=post.target_channels, file_name=post.file_name, file_type=post.file_type, file_id=post.file_id, thumbnail_url=post.thumbnail_url)
    return updated


@router.delete("")
async def delete_all_scheduled_posts():
    from ...services.database import delete_all_scheduled_posts as delete_all
    await delete_all()
    return {"message": "All scheduled posts deleted"}
