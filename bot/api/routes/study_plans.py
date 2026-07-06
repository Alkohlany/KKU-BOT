import json
import os
import httpx
from hijri_converter import Hijri
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


def to_arabic_numerals(number: int) -> str:
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    return "".join(arabic_digits[int(d)] for d in str(number))


async def update_group_post(group_id: int, force_new: bool = False):
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            return

        plans_stmt = select(StudyPlan).where(
            StudyPlan.group_id == group_id,
            StudyPlan.is_active == True
        ).order_by(StudyPlan.channel_message_id.asc().nullslast())
        plans_result = await session.execute(plans_stmt)
        all_plans = plans_result.scalars().all()

        published = [p for p in all_plans if p.channel_message_id]
        if not published and not group.channel_message_id:
            return

        channel_username = CHANNEL_ID.replace("@", "")

        today = Hijri.today()
        arabic_year = to_arabic_numerals(today.year)
        text = f"{group.title} {arabic_year}هـ\n"
        for plan in all_plans:
            if plan.channel_message_id:
                plan_link = f"https://t.me/{channel_username}/{plan.channel_message_id}"
                text += f"{plan.title} 🔻\n{plan_link}\n\n"
            else:
                text += f"{plan.title}\n\n"

        text += "🔴انظموا لقروب جامعة الملك خالد العام\n"
        text += "https://t.me/KKU_Main1\n\n"
        text += "🟢 انظمو لقروب الواتساب العام\n"
        text += "https://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n"
        text += "#شاركها_فربما_يبحث_عنها_غيرك"

        async with httpx.AsyncClient() as client:
            if group.channel_message_id and not force_new:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                    data={
                        "chat_id": CHANNEL_ID,
                        "message_id": group.channel_message_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    },
                    timeout=30
                )
            else:
                if force_new and group.channel_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": CHANNEL_ID, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                    group.channel_message_id = None
                    await session.commit()

                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={
                        "chat_id": CHANNEL_ID,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
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


@router.put("/groups/{group_id}")
async def update_study_plan_group_endpoint(group_id: int, data: StudyPlanGroupCreate):
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if data.title is not None:
            group.title = data.title
        if data.description is not None:
            group.description = data.description
        if data.group_tag is not None:
            group.group_tag = data.group_tag
        await session.commit()

    await update_group_post(group_id)
    return {"id": group_id, "title": data.title, "message": "Group updated successfully"}


@router.delete("/groups/{group_id}")
async def delete_study_plan_group_endpoint(group_id: int, mode: str = "permanent"):
    if mode == "reset":
        async with async_session() as session:
            stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            if not group:
                return {"error": "المجموعة غير موجودة"}

            plans_stmt = select(StudyPlan).where(StudyPlan.group_id == group_id)
            plans_result = await session.execute(plans_stmt)
            all_plans = plans_result.scalars().all()

            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                if group.channel_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": CHANNEL_ID, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                    group.channel_message_id = None

                for plan in all_plans:
                    if plan.channel_message_id:
                        try:
                            await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                                data={"chat_id": CHANNEL_ID, "message_id": plan.channel_message_id},
                                timeout=30
                            )
                        except Exception:
                            pass
                        plan.channel_message_id = None

            await session.commit()
            return {"message": "تم حذف جميع المنشورات من القناة وإعادة تعيين المجموعة", "mode": "reset"}
    else:
        await delete_study_plan_group(group_id)
        return {"status": "deleted", "mode": "permanent"}


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
    return await add_study_plan(title=data.title,
                               plan_url=data.plan_url, file_url=data.file_url,
                               group_id=data.group_id)


@router.post("/upload")
async def upload_study_plan(
    title: str = Form(...),
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

        old_group_message_id = group.channel_message_id
        old_plan_ids = {plan.id: plan.channel_message_id for plan in all_plans if plan.channel_message_id}

        if not all_plans:
            return {"message": "لا توجد خطط في هذه المجموعة"}

        published_count = 0
        failed_plans = []
        batch_size = 10

        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            for i in range(0, len(all_plans), batch_size):
                batch = all_plans[i:i + batch_size]
                media = []
                files = {}

                for idx, plan in enumerate(batch):
                    file_key = f"file_{idx}"

                    if not plan.file_url:
                        failed_plans.append(plan.title)
                        continue

                    pdf_content = None
                    for dl_attempt in range(3):
                        try:
                            file_resp = await client.get(plan.file_url, timeout=90)
                            if file_resp.status_code == 200:
                                pdf_content = file_resp.content
                                break
                            else:
                                print(f"Cloudinary download attempt {dl_attempt+1} failed: status={file_resp.status_code}, url={plan.file_url[:100]}")
                        except Exception as e:
                            print(f"Cloudinary download attempt {dl_attempt+1} exception: {e}, url={plan.file_url[:100]}")
                        if dl_attempt < 2:
                            await asyncio.sleep(2)

                    if not pdf_content:
                        failed_plans.append(plan.title)
                        continue

                    caption = ""
                    if group.group_tag:
                        caption += f"#{group.group_tag}\n"
                    caption += f"تخصص - {plan.title}\n\n"
                    caption += f'<blockquote>t.me/kkunewbot</blockquote>'

                    filename = f"{plan.title}.pdf"
                    files[file_key] = (filename, pdf_content, "application/pdf")
                    media.append({
                        "type": "document",
                        "media": f"attach://{file_key}",
                        "caption": caption,
                        "parse_mode": "HTML"
                    })

                if not media:
                    continue

                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
                    files=files,
                    data={"chat_id": CHANNEL_ID, "media": json.dumps(media)},
                    timeout=120
                )

                if resp.status_code == 200 and resp.json().get("ok"):
                    messages = resp.json()["result"]
                    for j, msg in enumerate(messages):
                        batch[j].channel_message_id = msg["message_id"]
                        published_count += 1
                else:
                    failed_plans.extend(p.title for p in batch)

        await session.commit()

        # Delete old messages only after new ones are sent
        if old_group_message_id or old_plan_ids:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as del_client:
                if old_group_message_id:
                    try:
                        await del_client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": CHANNEL_ID, "message_id": old_group_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                for plan in all_plans:
                    old_id = old_plan_ids.get(plan.id)
                    if old_id:
                        try:
                            await del_client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                                data={"chat_id": CHANNEL_ID, "message_id": old_id},
                                timeout=30
                            )
                        except Exception:
                            pass

        if published_count > 0:
            await update_group_post(group_id)

        result_text = f"تم نشر {published_count} خطة بنجاح"
        if failed_plans:
            result_text += f"\nفشل نشر {len(failed_plans)} خطة"

        return {"message": result_text, "published": published_count, "failed": failed_plans}


@router.post("/publish-plan/{plan_id}")
async def publish_single_plan(plan_id: int):
    """نشر خطة واحدة على القناة"""
    async with async_session() as session:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            return {"error": "الخطة غير موجودة"}
        if not plan.file_url:
            return {"error": "الخطة لا تحتوي على ملف مرفوع"}

        group = None
        if plan.group_id:
            g_stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == plan.group_id)
            g_result = await session.execute(g_stmt)
            group = g_result.scalar_one_or_none()

        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            pdf_content = None
            for dl_attempt in range(3):
                try:
                    file_resp = await client.get(plan.file_url, timeout=90)
                    if file_resp.status_code == 200:
                        pdf_content = file_resp.content
                        break
                    else:
                        print(f"Cloudinary download attempt {dl_attempt+1} failed: status={file_resp.status_code}, url={plan.file_url[:100]}")
                except Exception as e:
                    print(f"Cloudinary download attempt {dl_attempt+1} exception: {e}, url={plan.file_url[:100]}")
                if dl_attempt < 2:
                    import asyncio
                    await asyncio.sleep(2)

            if not pdf_content:
                return {"error": "فشل تحميل الملف من Cloudinary"}

            caption = ""
            if group and group.group_tag:
                caption += f"#{group.group_tag}\n"
            caption += f"تخصص - {plan.title}\n\n"
            caption += f'<blockquote>t.me/kkunewbot</blockquote>'

            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={
                    "chat_id": CHANNEL_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                },
                files={"document": (f"{plan.title}.pdf", pdf_content, "application/pdf")},
                timeout=120
            )

            if resp.status_code == 200 and resp.json().get("ok"):
                old_message_id = plan.channel_message_id
                if old_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": CHANNEL_ID, "message_id": old_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                plan.channel_message_id = resp.json()["result"]["message_id"]
                await session.commit()

                if group:
                    await update_group_post(group.id, force_new=True)

                return {"message": f"تم نشر {plan.title} بنجاح", "plan_id": plan.id}
            else:
                return {"error": f"فشل النشر: {resp.text}"}


@router.get("/file/{filename}")
async def get_study_plan_file(filename: str):
    raise HTTPException(status_code=404, detail="Files are stored on Cloudinary. Use the file_url from the API response.")


@router.put("/{plan_id}")
async def update_study_plan(
    plan_id: int,
    title: str = Form(None),
    group_id: int = Form(None),
    file: UploadFile = File(None)
):
    async with async_session() as session:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        old_group_id = plan.group_id

        if title is not None:
            plan.title = title
        if group_id is not None:
            plan.group_id = group_id

        new_group_id = plan.group_id

        if file:
            content = await file.read()
            file_url = upload_raw(content, filename=file.filename, folder="kku-bot/plans")
            plan.plan_url = file_url

        await session.commit()

    if old_group_id and old_group_id != new_group_id:
        await update_group_post(old_group_id)
    if new_group_id:
        await update_group_post(new_group_id)

    return {"message": "Study plan updated successfully", "id": plan_id}


@router.delete("/{plan_id}")
async def delete_study_plan_endpoint(plan_id: int):
    async with async_session() as session:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()
        group_id = plan.group_id if plan else None

    await delete_study_plan(plan_id)

    if group_id:
        await update_group_post(group_id)

    return {"status": "deleted"}
