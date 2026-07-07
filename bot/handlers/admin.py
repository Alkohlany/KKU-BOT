from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ChatMemberStatus
from bot.config import ADMIN_IDS
from bot.services.cloud_storage import upload_raw
from bot.services.database import (
    ban_user, is_banned, get_auto_responses,
    add_auto_response, remove_auto_response, get_user,
    get_auto_responses_by_source, remove_auto_responses_by_source,
    async_session
)
import cloudinary.uploader
import logging
from sqlalchemy import select, delete
from bot.models.models import BannedUser, User, Group, ActivityLog, AutoResponse

logger = logging.getLogger(__name__)


def detect_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'photo'
    if ext in ('mp4', 'avi', 'mov', 'mkv'):
        return 'video'
    return 'document'


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text("⚠️ الاستخدام: /ban <user_id> [سبب]")
        return

    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else None

        if await is_banned(target_id):
            await update.message.reply_text("⚠️ هذا المستخدم محظور بالفعل.")
            return

        await ban_user(target_id, reason, update.effective_user.id)
        await update.message.reply_text(f"✅ تم حظر المستخدم {target_id}")

    except ValueError:
        await update.message.reply_text("❌ يجب إدخال معرّف مستخدم صحيح.")


async def add_response_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ الاستخدام: /add_response <كلمة> <رد>")
        return

    keyword = context.args[0]
    response = " ".join(context.args[1:])

    await add_auto_response(keyword, response, update.effective_user.id)
    await update.message.reply_text(f"✅ تم إضافة الرد التلقائي للكلمة: {keyword}")


async def list_responses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    responses = await get_auto_responses()
    if not responses:
        await update.message.reply_text("📭 لا توجد ردود تلقائية.")
        return

    text = "📋 الردود التلقائية:\n\n"
    for r in responses:
        text += f"• {r.id}. {r.keyword} → {r.response[:50]}...\n"

    await update.message.reply_text(text)


async def del_response_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ الاستخدام: /del_response <id>")
        return

    try:
        response_id = int(context.args[0])
        await remove_auto_response(response_id)
        await update.message.reply_text(f"✅ تم حذف الرد التلقائي رقم {response_id}")
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text("⚠️ الاستخدام: /unban <user_id>")
        return

    try:
        target_id = int(context.args[0])

        if not await is_banned(target_id):
            await update.message.reply_text("⚠️ هذا المستخدم غير محظور.")
            return

        async with async_session() as session:
            await session.execute(
                delete(BannedUser).where(BannedUser.telegram_id == target_id)
            )
            await session.commit()

        await update.message.reply_text(f"✅ تم إلغاء حظر المستخدم {target_id}")

    except ValueError:
        await update.message.reply_text("❌ يجب إدخال معرّف مستخدم صحيح.")


async def banned_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    async with async_session() as session:
        result = await session.execute(select(BannedUser))
        banned_users = result.scalars().all()

    if not banned_users:
        await update.message.reply_text("📭 لا يوجد مستخدمين محظورين.")
        return

    text = "🚫 قائمة المحظورين:\n\n"
    for b in banned_users:
        text += f"• ID: {b.telegram_id} | السبب: {b.reason or 'غير محدد'} | التاريخ: {b.banned_at.strftime('%Y-%m-%d') if b.banned_at else 'غير معروف'}\n"

    await update.message.reply_text(text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    async with async_session() as session:
        user_result = await session.execute(select(User))
        users = user_result.scalars().all()
        user_count = len(users)

        group_result = await session.execute(select(Group))
        groups = group_result.scalars().all()
        group_count = len(groups)

        banned_result = await session.execute(select(BannedUser))
        banned_users = banned_result.scalars().all()
        banned_count = len(banned_users)

    text = (
        f"📊 إحصائيات البوت:\n\n"
        f"👥 عدد المستخدمين: {user_count}\n"
        f"👥 عدد القروبات: {group_count}\n"
        f"🚫 عدد المحظورين: {banned_count}"
    )
    await update.message.reply_text(text)


async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    async with async_session() as session:
        result = await session.execute(select(Group))
        groups = result.scalars().all()

    if not groups:
        await update.message.reply_text("📭 لا توجد قروبات متصلة بالبوت.")
        return

    text = "📋 قائمة القروبات المتصلة:\n\n"
    for g in groups:
        text += f"• {g.title or 'غير محدد'} | ID: {g.chat_id} | نشط: {'✅' if g.is_active else '❌'}\n"

    await update.message.reply_text(text)


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10)
        )
        logs = result.scalars().all()

    if not logs:
        await update.message.reply_text("📭 لا توجد سجلات نشاط.")
        return

    text = "📝 آخر 10 نشاطات:\n\n"
    for log in logs:
        text += f"• {log.action}: {log.details or 'بدون تفاصيل'} ({log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else 'غير معروف'})\n"

    await update.message.reply_text(text)


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
        await update.message.reply_text("❌ ليس لديك صلاحية لأداء هذا الأمر")
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
        if not keywords_part:
            await update.message.reply_text("❌ يرجى كتابة الكلمات المفتاحية بعد الأمر. مثال:\nاضافه رد قانون, قوانين")
            return

        keywords = [k.strip() for k in keywords_part.split(",") if k.strip()]
        if not keywords:
            await update.message.reply_text("❌ لم يتم العثور على كلمات مفتاحية صحيحة")
            return

        replied = update.message.reply_to_message
        response_text = replied.text or replied.caption or ""
        file_url = None
        file_type = None

        try:
            if replied.photo:
                file_obj = replied.photo[-1]
                file_type = "photo"
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                result = cloudinary.uploader.upload(bytes(file_bytes), folder="kku-bot/responses", resource_type="image")
                file_url = result["secure_url"]
            elif replied.video:
                file_obj = replied.video
                file_type = "video"
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                result = cloudinary.uploader.upload(bytes(file_bytes), folder="kku-bot/responses", resource_type="video")
                file_url = result["secure_url"]
            elif replied.document:
                file_obj = replied.document
                file_type = detect_file_type(file_obj.file_name or "file.pdf")
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
                file_type = file_type
            elif replied.voice or replied.audio:
                file_obj = replied.voice or replied.audio
                file_type = "document"
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

ban_handler = CommandHandler("ban", ban_command)
unban_handler = CommandHandler("unban", unban_command)
banned_list_handler = CommandHandler("banned_list", banned_list_command)
stats_handler = CommandHandler("stats", stats_command)
groups_handler = CommandHandler("groups", groups_command)
log_handler = CommandHandler("log", log_command)
add_response_handler = CommandHandler("add_response", add_response_command)
list_responses_handler = CommandHandler("list_responses", list_responses_command)
del_response_handler = CommandHandler("del_response", del_response_command)
