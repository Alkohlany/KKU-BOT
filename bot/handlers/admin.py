from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.constants import ChatMemberStatus
from bot.config import ADMIN_IDS
from bot.services.cloud_storage import upload_raw
from bot.services.database import (
    get_auto_responses_by_source, remove_auto_responses_by_source,
    async_session
)
import cloudinary.uploader
import logging
from bot.models.models import AutoResponse

logger = logging.getLogger(__name__)


def detect_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'photo'
    if ext in ('mp4', 'avi', 'mov', 'mkv'):
        return 'video'
    return 'document'


async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.reply_to_message:
        return

    text = update.message.text.strip()
    user = update.effective_user
    chat = update.effective_chat

    is_chat_admin = False
    try:
        member = await chat.get_member(user.id)
        is_chat_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        pass

    is_bot_admin = user.id in context.bot_data.get('admin_ids', [])

    if not is_chat_admin and not is_bot_admin:
        return

    target_user = update.message.reply_to_message.from_user
    target_user_id = target_user.id

    try:
        target_member = await chat.get_member(target_user_id)
        if target_member.status in [ChatMemberStatus.OWNER]:
            await update.message.reply_text("❌ لا يمكنك تنفيذ هذا الأمر على مالك القروب")
            return
    except:
        pass

    if text in ["حذف", "ازالة", "امسح"]:
        try:
            await update.message.reply_to_message.delete()
            await update.message.reply_text(f"✅ تم حذف رسالة {target_user.first_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل في حذف الرسالة: {e}")

    elif text in ["حظر", "ban"]:
        try:
            await chat.ban_member(target_user_id)
            await update.message.reply_to_message.delete()
            await update.message.reply_text(f"🚫 تم حظر {target_user.first_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل في حظر المستخدم: {e}")

    elif text in ["الغاء حظر", "unban"]:
        try:
            await chat.unban_member(target_user_id)
            await update.message.reply_text(f"✅ تم إلغاء حظر {target_user.first_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل في إلغاء الحظر: {e}")

    elif text in ["طرد", "kick"]:
        try:
            await chat.ban_member(target_user_id)
            await chat.unban_member(target_user_id)
            await update.message.reply_to_message.delete()
            await update.message.reply_text(f"👢 تم طرد {target_user.first_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل في طرد المستخدم: {e}")

    elif text in ["تثبيت", "pin"]:
        try:
            await update.message.reply_to_message.pin()
            await update.message.reply_text(f"📌 تم تثبيت رسالة {target_user.first_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل في تثبيت الرسالة: {e}")

    elif text.startswith("اضافه رد"):
        keywords_part = text[len("اضافه رد"):].strip()
        replied = update.message.reply_to_message
        response_text = replied.text or replied.caption or ""
        file_url = None
        file_type = None

        if not response_text and not (replied.photo or replied.video or replied.document or replied.voice or replied.audio):
            await update.message.reply_text("❌ يجب أن تحتوي الرسالة المُشار إليها على نص أو مرفق")
            return

        if keywords_part:
            keywords_part = keywords_part.replace("،", ",")
            keywords = [k.strip() for k in keywords_part.split(",") if k.strip()]
        else:
            if not response_text:
                await update.message.reply_text("❌ الرسالة لا تحتوي على نص لتحليله")
                return
            await update.message.reply_text("🤖 جاري تحليل المحتوى باستخدام الذكاء الاصطناعي...")
            try:
                from bot.services.ai import extract_keywords_and_questions
                items = extract_keywords_and_questions(response_text)
                keywords = items
            except Exception as e:
                logger.error(f"AI generation error: {e}")
                await update.message.reply_text(f"❌ فشل في تحليل المحتوى آليًا. الرجاء كتابة الكلمات المفتاحية يدويًا.\n({e})")
                return

        if not keywords:
            await update.message.reply_text("❌ لم يتم العثور على كلمات مفتاحية صحيحة")
            return

        file_tg_id = None
        try:
            if replied.photo:
                file_obj = replied.photo[-1]
                file_type = "photo"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                result = cloudinary.uploader.upload(bytes(file_bytes), folder="kku-bot/responses", resource_type="image")
                file_url = result["secure_url"]
            elif replied.video:
                file_obj = replied.video
                file_type = "video"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                result = cloudinary.uploader.upload(bytes(file_bytes), folder="kku-bot/responses", resource_type="video")
                file_url = result["secure_url"]
            elif replied.document:
                file_obj = replied.document
                file_type = detect_file_type(file_obj.file_name or "file.pdf")
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                if file_type in ("photo", "image"):
                    result = cloudinary.uploader.upload(bytes(file_bytes), folder="kku-bot/responses", resource_type="image")
                    file_url = result["secure_url"]
                elif file_type == "video":
                    result = cloudinary.uploader.upload(bytes(file_bytes), folder="kku-bot/responses", resource_type="video")
                    file_url = result["secure_url"]
                else:
                    file_url = upload_raw(bytes(file_bytes), filename=file_obj.file_name or "file", folder="kku-bot/responses")
            elif replied.voice or replied.audio:
                file_obj = replied.voice or replied.audio
                file_type = "document"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_raw(bytes(file_bytes), filename="audio", folder="kku-bot/responses")
        except Exception as e:
            logger.warning(f"Could not upload file from replied message: {e}")

        created_count = 0
        for keyword in keywords:
            try:
                ar = AutoResponse(
                    keyword=keyword,
                    response=response_text,
                    created_by=user.id,
                    file_url=file_url,
                    file_type=file_type,
                    file_tg_id=file_tg_id,
                    source_chat_id=chat.id,
                    source_message_id=replied.message_id,
                )
                async with async_session() as session:
                    session.add(ar)
                    await session.commit()
                created_count += 1
            except Exception as e:
                logger.error(f"Could not create auto response for keyword '{keyword}': {e}")

        if created_count > 0:
            await update.message.reply_text(f"✅ تم إضافة {created_count} رد تلقائي:\n{', '.join(keywords)}")
        else:
            await update.message.reply_text("❌ فشل في إنشاء الردود التلقائية")

    elif text.strip() in ["ازاله الرد", "ازالة الرد"]:
        replied = update.message.reply_to_message
        responses = await get_auto_responses_by_source(chat.id, replied.message_id)
        if not responses:
            await update.message.reply_text("❌ لا توجد ردود تلقائية مرتبطة بهذه الرسالة")
            return

        keywords = [r.keyword for r in responses]
        await remove_auto_responses_by_source(chat.id, replied.message_id)
        await update.message.reply_text(f"✅ تم إزالة {len(responses)} رد تلقائي:\n{', '.join(keywords)}")


admin_reply = MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.GROUPS, admin_reply_handler)
