from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from bot.services.database import get_db
from bot.api.auth import get_current_user
from bot.models.models import AutoResponse
import cloudinary.uploader
from bot.services.cloud_storage import upload_raw
from bot.services.database import add_auto_response, update_auto_response

router = APIRouter()


class CustomResponseCreate(BaseModel):
    keyword: str
    response: str
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    as_document: bool = False


class CustomResponseUpdate(BaseModel):
    keyword: Optional[str] = None
    response: Optional[str] = None
    enabled: Optional[bool] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    as_document: Optional[bool] = None


def detect_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'photo'
    if ext in ('mp4', 'avi', 'mov', 'mkv'):
        return 'video'
    return 'document'


@router.get("")
async def get_custom_responses(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AutoResponse))
    items = result.scalars().all()
    return [
        {
            "id": r.id,
            "keyword": r.keyword,
            "response": r.response,
            "enabled": r.is_active,
            "file_url": r.file_url,
            "file_type": r.file_type,
            "as_document": r.as_document,
        }
        for r in items
    ]


@router.post("")
async def create_custom_response(
    data: CustomResponseCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ar = await add_auto_response(
        keyword=data.keyword, response=data.response, created_by=0,
        file_url=data.file_url, file_type=data.file_type, as_document=data.as_document
    )
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active, "file_url": ar.file_url, "file_type": ar.file_type, "as_document": ar.as_document}


@router.post("/upload")
async def upload_custom_response(
    keyword: str = Form(...),
    response: str = Form(...),
    file: UploadFile = File(None),
    as_document: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    file_url = None
    file_type = None
    if file:
        content = await file.read()
        file_type = detect_file_type(file.filename)
        if file_type in ('image', 'photo'):
            result = cloudinary.uploader.upload(content, folder="kku-bot/responses", resource_type="image")
            file_url = result["secure_url"]
        elif file_type == 'video':
            result = cloudinary.uploader.upload(content, folder="kku-bot/responses", resource_type="video")
            file_url = result["secure_url"]
        else:
            file_url = upload_raw(content, filename=file.filename, folder="kku-bot/responses")

    ar = AutoResponse(keyword=keyword, response=response, created_by=0, file_url=file_url, file_type=file_type, as_document=as_document)
    db.add(ar)
    await db.commit()
    await db.refresh(ar)
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active, "file_url": ar.file_url, "file_type": ar.file_type, "as_document": ar.as_document}


@router.put("/{response_id}")
async def update_custom_response(
    response_id: int,
    data: CustomResponseUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ar = await update_auto_response(
        response_id=response_id,
        keyword=data.keyword,
        response=data.response,
        is_active=data.enabled,
        file_url=data.file_url,
        file_type=data.file_type,
        as_document=data.as_document,
    )
    if not ar:
        raise HTTPException(status_code=404, detail="Response not found")
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active, "file_url": ar.file_url, "file_type": ar.file_type, "as_document": ar.as_document}


@router.put("/upload/{response_id}")
async def upload_update_custom_response(
    response_id: int,
    keyword: str = Form(None),
    response: str = Form(None),
    file: UploadFile = File(None),
    as_document: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AutoResponse).where(AutoResponse.id == response_id))
    ar = result.scalar_one_or_none()
    if not ar:
        raise HTTPException(status_code=404, detail="Response not found")

    if keyword is not None:
        ar.keyword = keyword
    if response is not None:
        ar.response = response
    if as_document is not None:
        ar.as_document = as_document
    if file:
        content = await file.read()
        file_type = detect_file_type(file.filename)
        if file_type in ('image', 'photo'):
            result = cloudinary.uploader.upload(content, folder="kku-bot/responses", resource_type="image")
            ar.file_url = result["secure_url"]
        elif file_type == 'video':
            result = cloudinary.uploader.upload(content, folder="kku-bot/responses", resource_type="video")
            ar.file_url = result["secure_url"]
        else:
            ar.file_url = upload_raw(content, filename=file.filename, folder="kku-bot/responses")
        ar.file_type = file_type

    await db.commit()
    return {"id": ar.id, "keyword": ar.keyword, "response": ar.response, "enabled": ar.is_active, "file_url": ar.file_url, "file_type": ar.file_type, "as_document": ar.as_document}


@router.delete("/{response_id}")
async def delete_custom_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await db.execute(delete(AutoResponse).where(AutoResponse.id == response_id))
    await db.commit()
    return {"success": True}
