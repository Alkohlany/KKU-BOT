import json
import os
import asyncio
import tempfile
import httpx
import fitz
from hijri_converter import Hijri
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from bot.models.models import StudyPlan, StudyPlanGroup, ChannelGroup
from bot.services.database import (
    async_session, add_study_plan, get_all_study_plans, get_study_plans_by_faculty,
    delete_study_plan, get_all_study_plan_groups, get_study_plan_group_by_id,
    create_study_plan_group, delete_study_plan_group, get_study_plans_by_group,
    update_study_plan_group, get_active_channel_groups, get_official_channel
)
from bot.services.cloud_storage import upload_raw
from bot.config import BOT_TOKEN

router = APIRouter()


async def _get_channel_id():
    """Get the official channel chat_id from the database"""
    official = await get_official_channel()
    if official:
        return official.chat_id
    channels = await get_active_channel_groups()
    for ch in channels:
        if ch.type == 'channel':
            return ch.chat_id
    return None


async def _get_channel_username():
    """Get the channel username from the database for generating links"""
    official = await get_official_channel()
    if official and official.invite_link:
        link = official.invite_link
        if 't.me/' in link:
            return link.split('t.me/')[-1].strip('/')
    if official:
        return str(official.chat_id)

    async with async_session() as session:
        stmt = select(ChannelGroup).where(
            ChannelGroup.type == 'channel',
            ChannelGroup.is_active == True
        ).order_by(ChannelGroup.created_at.desc()).limit(1)
        result = await session.execute(stmt)
        channel = result.scalar_one_or_none()
        if channel and channel.invite_link:
            link = channel.invite_link
            if 't.me/' in link:
                return link.split('t.me/')[-1].strip('/')
        if channel:
            return str(channel.chat_id)
        return None


def _generate_pdf_thumbnail(pdf_bytes: bytes, folder: str = "kku-bot/plans") -> str | None:
    """Generate a JPEG thumbnail from PDF bytes, upload to R2, return URL or None."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            thumb_path = tmp_path.rsplit('.', 1)[0] + '_thumb.jpg'
            pix.save(thumb_path)
            with open(thumb_path, 'rb') as f:
                thumb_bytes = f.read()
            thumb_url = upload_raw(thumb_bytes, filename="thumb.jpg", folder=folder)
            os.unlink(thumb_path)
            doc.close()
            os.unlink(tmp_path)
            return thumb_url
        doc.close()
        os.unlink(tmp_path)
    except Exception:
        pass
    return None


def _generate_pdf_thumbnail_bytes(pdf_bytes: bytes) -> bytes | None:
    """Generate a JPEG thumbnail from PDF bytes, return resized bytes for upload."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            thumb_path = tmp_path.rsplit('.', 1)[0] + '_thumb.jpg'
            pix.save(thumb_path)
            with open(thumb_path, 'rb') as f:
                thumb_bytes = f.read()
            os.unlink(thumb_path)
            doc.close()
            os.unlink(tmp_path)
            try:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(thumb_bytes))
                img.thumbnail((320, 320), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, "JPEG", quality=85)
                return buf.getvalue()
            except Exception:
                return thumb_bytes
        doc.close()
        os.unlink(tmp_path)
    except Exception:
        pass
    return None


def to_arabic_numerals(number: int) -> str:
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    return "".join(arabic_digits[int(d)] for d in str(number))


def _build_plan_caption(group, plan_title):
    """Build plan caption using group's specialization and link"""
    caption = ""
    if group and group.group_tag:
        caption += f"#{group.group_tag}\n"
    spec = group.specialization if group and group.specialization else "تخصص"
    caption += f"تخصص - {spec}\n\n"
    link = group.link if group and group.link else "t.me/kkunewbot"
    caption += f'<blockquote>{link}</blockquote>'
    return caption


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

        if not published:
            if group.channel_message_id:
                channel_chat_id = await _get_channel_id()
                async with httpx.AsyncClient() as client:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                group.channel_message_id = None
                await session.commit()
            return

        channel_chat_id = await _get_channel_id()
        channel_username = await _get_channel_username()
        if not channel_username:
            return

        today = Hijri.today()
        arabic_year = to_arabic_numerals(today.year)
        text = f"{group.title} {arabic_year}هـ\n"
        for plan in published:
            plan_link = f"https://t.me/{channel_username}/{plan.channel_message_id}"
            text += f"{plan.title} 🔻\n{plan_link}\n\n"

        text += "🔴انظموا لقروب جامعة الملك خالد العام\n"
        text += "https://t.me/KKU_Main1\n\n"
        text += "🟢 انظمو لقروب الواتساب العام\n"
        text += "https://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n"
        text += "#شاركها_فربما_يبحث_عنها_غيرك"

        channel_chat_id = await _get_channel_id()

        async with httpx.AsyncClient() as client:
            if group.channel_message_id and not force_new:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                    data={
                        "chat_id": channel_chat_id,
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
                            data={"chat_id": channel_chat_id, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                    group.channel_message_id = None
                    await session.commit()

                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={
                        "chat_id": channel_chat_id,
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


async def _update_published_plan_captions(group_id: int):
    """Update captions of all published plans in a group"""
    async with async_session() as session:
        stmt = select(StudyPlanGroup).where(StudyPlanGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()
        if not group:
            return

        plans_stmt = select(StudyPlan).where(
            StudyPlan.group_id == group_id,
            StudyPlan.is_active == True,
            StudyPlan.channel_message_id.isnot(None)
        )
        plans_result = await session.execute(plans_stmt)
        plans = plans_result.scalars().all()

        if not plans:
            return

        channel_chat_id = await _get_channel_id()
        new_caption = _build_plan_caption(group, "{title}")

        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            for plan in plans:
                caption = _build_plan_caption(group, plan.title)
                try:
                    await client.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption",
                        data={
                            "chat_id": channel_chat_id,
                            "message_id": plan.channel_message_id,
                            "caption": caption,
                            "parse_mode": "HTML"
                        },
                        timeout=30
                    )
                except Exception as e:
                    print(f"Failed to update caption for plan {plan.id}: {e}")


class StudyPlanGroupCreate(BaseModel):
    title: str
    description: Optional[str] = None
    group_tag: Optional[str] = None
    specialization: Optional[str] = None
    link: Optional[str] = None


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
    group = await create_study_plan_group(title=data.title, description=data.description, group_tag=data.group_tag, specialization=data.specialization, link=data.link)

    try:
        channel_chat_id = await _get_channel_id()
        channel_username = await _get_channel_username()
        if channel_username and group.group_tag:
            link = group.link or f"https://t.me/{channel_username.replace('@', '')}"
            text = f"📂 {group.title}\n"
            text += f"#{group.group_tag}\n"
            if group.specialization:
                text += f"{group.specialization}\n"
            text += f"{link}"
        else:
            text = f"📂 {group.title}\n"
            if group.description:
                text += f"{group.description}"

        async with httpx.AsyncClient() as client:
            data_payload = {"chat_id": channel_chat_id, "text": text}
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

    return {"id": group.id, "title": group.title, "group_tag": group.group_tag, "specialization": group.specialization, "link": group.link, "message": "Group created successfully"}


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
        if data.specialization is not None:
            group.specialization = data.specialization
        if data.link is not None:
            group.link = data.link
        await session.commit()

    await update_group_post(group_id)
    await _update_published_plan_captions(group_id)
    return {"id": group_id, "title": data.title, "group_tag": data.group_tag, "specialization": data.specialization, "link": data.link, "message": "Group updated successfully"}


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

            channel_chat_id = await _get_channel_id()

            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                if group.channel_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": group.channel_message_id},
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
                                data={"chat_id": channel_chat_id, "message_id": plan.channel_message_id},
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
@router.get("")
async def get_study_plans(group_id: Optional[int] = None, faculty: Optional[str] = None):
    if group_id:
        return await get_study_plans_by_group(group_id)
    if faculty:
        return await get_study_plans_by_faculty(faculty)
    return await get_all_study_plans()


@router.post("")
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

        channel_chat_id = await _get_channel_id()

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

                    from bot.services.cloud_storage import download_raw

                    pdf_content = None
                    last_status = None
                    for dl_attempt in range(3):
                        try:
                            file_resp = await client.get(plan.file_url, timeout=90)
                            if file_resp.status_code == 200:
                                pdf_content = file_resp.content
                                break
                            else:
                                last_status = file_resp.status_code
                                print(f"تحميل attempt {dl_attempt+1} failed: status={file_resp.status_code}, url={plan.file_url[:100]}")
                        except Exception as e:
                            last_status = 0
                            print(f"تحميل attempt {dl_attempt+1} exception: {e}, url={plan.file_url[:100]}")
                        if dl_attempt < 2:
                            await asyncio.sleep(2)

                    if not pdf_content:
                        pdf_content = await asyncio.to_thread(download_raw, plan.file_url)

                    if not pdf_content:
                        failed_plans.append(plan.title)
                        continue

                    caption = _build_plan_caption(group, plan.title)

                    file_ext = plan.file_url.split(".")[-1].split("?")[0].lower() if plan.file_url else "pdf"
                    is_image = file_ext in ("jpg", "jpeg", "png", "gif", "webp")

                    filename = f"{plan.title}.{file_ext}"

                    if is_image:
                        mime = "image/jpeg"
                        media_item = {
                            "type": "photo",
                            "media": f"attach://{file_key}",
                            "caption": caption,
                            "parse_mode": "HTML"
                        }
                    else:
                        mime = "application/pdf"
                        media_item = {
                            "type": "document",
                            "media": f"attach://{file_key}",
                            "caption": caption,
                            "parse_mode": "HTML"
                        }

                    files[file_key] = (filename, pdf_content, mime)
                    if not is_image:
                        thumb_bytes = _generate_pdf_thumbnail_bytes(pdf_content)
                        if thumb_bytes:
                            thumb_key = f"thumb_{idx}"
                            files[thumb_key] = ("thumb.jpg", thumb_bytes, "image/jpeg")
                            media_item["thumb"] = f"attach://{thumb_key}"
                    media.append(media_item)

                if not media:
                    continue

                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
                    files=files,
                    data={"chat_id": channel_chat_id, "media": json.dumps(media)},
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
                            data={"chat_id": channel_chat_id, "message_id": old_group_message_id},
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
                                data={"chat_id": channel_chat_id, "message_id": old_id},
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

        import asyncio
        from bot.services.cloud_storage import download_raw

        channel_chat_id = await _get_channel_id()

        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            pdf_content = None
            last_status = None
            for dl_attempt in range(3):
                try:
                    file_resp = await client.get(plan.file_url, timeout=90)
                    if file_resp.status_code == 200:
                        pdf_content = file_resp.content
                        break
                    else:
                        last_status = file_resp.status_code
                        print(f"تحميل attempt {dl_attempt+1} failed: status={file_resp.status_code}, url={plan.file_url[:100]}")
                except Exception as e:
                    last_status = 0
                    print(f"تحميل attempt {dl_attempt+1} exception: {e}, url={plan.file_url[:100]}")
                if dl_attempt < 2:
                    await asyncio.sleep(2)

            if not pdf_content:
                pdf_content = await asyncio.to_thread(download_raw, plan.file_url)

            if not pdf_content:
                return {"error": f"فشل تحميل الملف من الخدمة السحابية (status: {last_status})"}

            caption = _build_plan_caption(group, plan.title)

            thumb_bytes = _generate_pdf_thumbnail_bytes(pdf_content)
            send_data = {
                "chat_id": channel_chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            }

            files_dict = {"document": (f"{plan.title}.pdf", pdf_content, "application/pdf")}
            if thumb_bytes:
                files_dict["thumbnail"] = ("thumb.jpg", thumb_bytes, "image/jpeg")

            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data=send_data,
                files=files_dict,
                timeout=120
            )

            if resp.status_code == 200 and resp.json().get("ok"):
                old_message_id = plan.channel_message_id
                if old_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": old_message_id},
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
    raise HTTPException(status_code=404, detail="Use the file_url from the API response.")


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
async def delete_study_plan_endpoint(plan_id: int, mode: str = "permanent"):
    if mode == "reset":
        async with async_session() as session:
            stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            if not plan:
                return {"error": "الخطة غير موجودة"}
            
            group_id = plan.group_id

            if plan.channel_message_id:
                channel_chat_id = await _get_channel_id()
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": plan.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                plan.channel_message_id = None
                await session.commit()

            if group_id:
                await update_group_post(group_id)

            return {"message": "تم حذف الخطة من القناة", "mode": "reset"}
    else:
        async with async_session() as session:
            stmt = select(StudyPlan).where(StudyPlan.id == plan_id)
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            group_id = plan.group_id if plan else None

        await delete_study_plan(plan_id)

        if group_id:
            await update_group_post(group_id)

        return {"status": "deleted", "mode": "permanent"}
