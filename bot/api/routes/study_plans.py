import os
import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
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
from bot.config import BOT_TOKEN, CHANNEL_ID

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def update_group_post(group_id: int):
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if not group or not group.channel_message_id:
            return

        plans_stmt = select(StudyPlan).where(
            StudyPlan.group_id == group_id,
            StudyPlan.is_active == True
        )
        plans_result = await session.execute(plans_stmt)
        all_plans = plans_result.scalars().all()

        channel_username = CHANNEL_ID.replace("@", "")

        text = f"📂 {group.title}\n"

        if group.description:
            text += f"{group.description}\n"

        text += "\n"

        for plan in all_plans:
            if plan.channel_message_id:
                plan_link = f"https://t.me/{channel_username}/{plan.channel_message_id}"
                text += f"{plan.title} ⬇️\n{plan_link}\n\n"
            else:
                text += f"{plan.title}\n\n"

        text += "\n🔴انظموا لقروب جامعة الملك خالد العام\n\nhttps://t.me/KKU_Main1 \n\n\nانظمو لقروب الواتساب العام\n\nhttps://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n#شاركها_فربما_يبحث_عنها_غيرك"

        async with httpx.AsyncClient() as client:
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

            if resp.status_code != 200:
                print(f"editMessageText failed: {resp.status_code} {resp.text}")
                return

            result = resp.json()
            if not result.get("ok"):
                print(f"editMessageText API error: {result}")


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
    file_path = None
    file_url = None
    if file:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        file_url = f"/api/study-plans/file/{file.filename}"

    plan = await add_study_plan(
        title=title,
        description=description,
        faculty=faculty,
        level=level,
        plan_url=file_path or plan_url,
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
            raise HTTPException(status_code=404, detail="Group not found")

        plans_stmt = select(StudyPlan).where(
            StudyPlan.group_id == group_id,
            StudyPlan.is_active == True,
            StudyPlan.channel_message_id == None
        )
        plans_result = await session.execute(plans_stmt)
        unpublished_plans = plans_result.scalars().all()

        if not unpublished_plans:
            return {"message": "لا توجد خطط غير منشورة"}

        published_count = 0
        async with httpx.AsyncClient() as client:
            for plan in unpublished_plans:
                caption = f"#{group.group_tag}\n" if group.group_tag else ""
                caption += f"تخصص - {plan.title}\n"
                caption += f"\n🔴انظموا لقروب جامعة الملك خالد العام\n\nhttps://t.me/KKU_Main1 \n\n\nانظمو لقروب الواتساب العام\n\nhttps://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W"

                try:
                    if plan.plan_url and os.path.exists(plan.plan_url):
                        with open(plan.plan_url, "rb") as f:
                            files = {"document": (os.path.basename(plan.plan_url), f, "application/octet-stream")}
                            data = {"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
                            resp = await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                                files=files,
                                data=data,
                                timeout=60
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
        return {"message": f"تم نشر {published_count} خطط بنجاح"}


@router.get("/file/{filename}")
async def get_study_plan_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


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
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            plan.plan_url = file_path

        await session.commit()
        return {"message": "Study plan updated successfully", "id": plan_id}


@router.delete("/{plan_id}")
async def delete_study_plan_endpoint(plan_id: int):
    await delete_study_plan(plan_id)
    return {"status": "deleted"}
