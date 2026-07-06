import os
import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from bot.models.models import StudyPlan, StudyPlanGroup
from bot.services.database import (
    async_session, add_study_plan, get_all_study_plans, get_study_plans_by_faculty,
    delete_study_plan, get_all_study_plan_groups, get_study_plan_group_by_id,
    create_study_plan_group, delete_study_plan_group, get_study_plans_by_group,
    update_study_plan_group
)
from bot.services.cloud_storage import upload_raw
from bot.config import BOT_TOKEN, CHANNEL_ID

router = APIRouter()


async def update_group_post(group_id: int):
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            return

        plans_stmt = select(StudyPlan).where(
            StudyPlan.group_id == group_id,
            StudyPlan.is_active == True
        )
        plans_result = await session.execute(plans_stmt)
        all_plans = plans_result.scalars().all()

        channel_username = CHANNEL_ID.replace("@", "")

        text = "📂 محدث خطط التخصصات 1447هـ\n"
        text += f"({group.title})\n"
        text += "تاريخ التحديث: ١٤٤٧هـ\n\n"

        for plan in all_plans:
            if plan.channel_message_id:
                plan_link = f"https://t.me/{channel_username}/{plan.channel_message_id}"
                text += f"خطة {plan.title} ⬇️\n{plan_link}\n\n"
            else:
                text += f"خطة {plan.title}\n\n"

        text += "🔴انظموا لقروب جامعة الملك خالد العام\n"
        text += "https://t.me/KKU_Main1\n\n"
        text += "🟢 انظمو لقروب الواتساب العام\n"
        text += "https://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n"
        text += "#شاركها_فربما_يبحث_عنها_غيرك"

        async with httpx.AsyncClient() as client:
            if group.channel_message_id:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                    data={
                        "chat_id": CHANNEL_ID,
                        "message_id": group.channel_message_id,
                        "text": text,
                        "parse_mode": "HTML"
                    },
                    timeout=30
                )
            else:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={
                        "chat_id": CHANNEL_ID,
                        "text": text,
                        "parse_mode": "HTML"
                    },
                    timeout=30
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("ok"):
                        group.channel_message_id = result["result"]["message_id"]
                        await session.commit()


class StudyPlanGroupCreate(BaseModel):
    title: str
    description: Optional[str] = None
    group_tag: Optional[str] = None


class StudyPlanCreate(BaseModel):
    title: str
    description: Optional[str] = None
    faculty: Optional[str] = None
    level: Optional[str] = None
    plan_url: Optional[str] = None
    file_url: Optional[str] = None
    group_id: Optional[int] = None


# ==================== Study Plan Groups ====================
@router.get("/groups")
async def get_study_plan_groups():
    return await get_all_study_plan_groups()


@router.get("/groups/{group_id}")
async def get_study_plan_group(group_id: int):
    group = await get_study_plan_group_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    plans = await get_study_plans_by_group(group_id)
    return {"group": group, "plans": plans}


@router.post("/groups")
async def create_study_plan_group_endpoint(data: StudyPlanGroupCreate):
    group = await create_study_plan_group(title=data.title, description=data.description, group_tag=data.group_tag)

    try:
        text = f"📂 {group.title}\n"
        if group.description:
            text += f"{group.description}"

        async with httpx.AsyncClient() as client:
            data_payload = {"chat_id": CHANNEL_ID, "text": text}
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data=data_payload,
                timeout=30
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get("ok"):
                    msg_id = result["result"]["message_id"]
                    await update_study_plan_group(group.id, channel_message_id=msg_id)
    except Exception as e:
        print(f"Error publishing group to channel: {e}")

    return {"id": group.id, "title": group.title, "group_tag": group.group_tag, "message": "Group created successfully"}


@router.delete("/groups/{group_id}")
async def delete_study_plan_group_endpoint(group_id: int):
    await delete_study_plan_group(group_id)
    return {"status": "deleted"}


# ==================== Study Plans ====================
@router.get("/")
async def get_study_plans(group_id: Optional[int] = None, faculty: Optional[str] = None):
    if group_id:
        return await get_study_plans_by_group(group_id)
    if faculty:
        return await get_study_plans_by_faculty(faculty)
    return await get_all_study_plans()


@router.post("/")
async def create_study_plan(data: StudyPlanCreate):
    return await add_study_plan(title=data.title, description=data.description,
                               faculty=data.faculty, level=data.level,
                               plan_url=data.plan_url, file_url=data.file_url,
                               group_id=data.group_id)


@router.post("/upload")
async def upload_study_plan(
    title: str = Form(...),
    description: str = Form(""),
    faculty: str = Form(""),
    level: str = Form(""),
    plan_url: str = Form(""),
    group_id: int = Form(None),
    file: Optional[UploadFile] = File(None),
):
    file_url = None
    if file:
        content = await file.read()
        file_url = upload_raw(content, filename=file.filename, folder="kku-bot/plans")

    plan = await add_study_plan(
        title=title,
        description=description,
        faculty=faculty,
        level=level,
        plan_url=plan_url,
        file_url=file_url,
        group_id=group_id,
    )

    return {"id": plan.id, "title": plan.title, "message": "تم حفظ الخطة كمسودة"}


@router.post("/publish-group/{group_id}")
async def publish_group_plans(group_id: int):
    """نشر جميع خطط المجموعة على القناة"""
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            return {"error": "المجموعة غير موجودة"}

        plans_stmt = select(StudyPlan).where(
            StudyPlan.group_id == group_id,
            StudyPlan.is_active == True
        )
        plans_result = await session.execute(plans_stmt)
        all_plans = plans_result.scalars().all()

        async with httpx.AsyncClient(follow_redirects=True) as client:
            if group.channel_message_id:
                try:
                    await client.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                        data={"chat_id": CHANNEL_ID, "message_id": group.channel_message_id},
                        timeout=30
                    )
                except Exception as e:
                    print(f"Error deleting group message: {e}")
                group.channel_message_id = None

            for plan in all_plans:
                if plan.channel_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": CHANNEL_ID, "message_id": plan.channel_message_id},
                            timeout=30
                        )
                    except Exception as e:
                        print(f"Error deleting plan message: {e}")
                    plan.channel_message_id = None

        await session.commit()

        if not all_plans:
            return {"message": "لا توجد خطط في هذه المجموعة"}

        published_count = 0
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for plan in all_plans:
                caption = f"ملف الخطه المرفق\n\n"
                if group.group_tag:
                    caption += f"#{group.group_tag}\n"
                caption += f"تخصص - {plan.title}\n\n"
                caption += f'<a href="https://t.me/kkunewbot">t.me/kkunewbot</a>'

                try:
                    if plan.file_url:
                        file_resp = await client.get(plan.file_url, timeout=60)
                        if file_resp.status_code == 200:
                            files = {"document": ("plan.pdf", file_resp.content, "application/pdf")}
                            data = {"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
                            resp = await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                                files=files,
                                data=data,
                                timeout=60
                            )
                        else:
                            data = {"chat_id": CHANNEL_ID, "text": caption + f"\n\n📎 {plan.file_url}", "parse_mode": "HTML"}
                            resp = await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                data=data,
                                timeout=30
                            )
                    else:
                        data = {"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"}
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            data=data,
                            timeout=30
                        )

                    if resp.status_code == 200:
                        result = resp.json()
                        if result.get("ok"):
                            plan.channel_message_id = result["result"]["message_id"]
                            published_count += 1
                except Exception as e:
                    print(f"Error publishing plan {plan.id}: {e}")

        await session.commit()

        await update_group_post(group_id)

        return {"message": f"تم نشر {published_count} خطة بنجاح"}


@router.get("/file/{filename}")
async def get_study_plan_file(filename: str):
    raise HTTPException(status_code=404, detail="Files are stored on Cloudinary. Use the file_url from the API response.")


@router.put("/{plan_id}")
async def update_study_plan(
    plan_id: int,
    title: str = Form(None),
    description: str = Form(None),
    faculty: str = Form(None),
    level: str = Form(None),
    group_id: int = Form(None),
    file: UploadFile = File(None)
):
    async with async_session() as session:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        if title is not None:
            plan.title = title
        if description is not None:
            plan.description = description
        if faculty is not None:
            plan.faculty = faculty
        if level is not None:
            plan.level = level
        if group_id is not None:
            plan.group_id = group_id

        if file:
            content = await file.read()
            file_url = upload_raw(content, filename=file.filename, folder="kku-bot/plans")
            plan.plan_url = file_url

        await session.commit()
        return {"message": "Study plan updated successfully", "id": plan_id}


@router.delete("/{plan_id}")
async def delete_study_plan_endpoint(plan_id: int):
    await delete_study_plan(plan_id)
    return {"status": "deleted"}
