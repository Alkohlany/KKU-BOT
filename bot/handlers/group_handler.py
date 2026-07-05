from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler, MessageHandler, filters, CommandHandler
from bot.services.database import add_group, get_group
import logging

logger = logging.getLogger(__name__)


async def track_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    new_member = update.chat_member.new_chat_member
    old_member = update.chat_member.old_chat_member
    was_member = old_member.status in ("member", "administrator", "creator")
    is_member = new_member.status in ("member", "administrator", "creator")
    if not was_member and is_member and new_member.user.id == context.bot.id:
        existing = await get_group(chat.id)
        if not existing:
            await add_group(chat_id=chat.id, title=chat.title)
            logger.info(f"Registered group via ChatMemberHandler: {chat.title} ({chat.id})")


async def track_group_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            existing = await get_group(chat.id)
            if not existing:
                await add_group(chat_id=chat.id, title=chat.title)
                logger.info(f"Registered group via NEW_CHAT_MEMBERS: {chat.title} ({chat.id})")
            else:
                logger.info(f"Group already registered: {chat.title} ({chat.id})")


async def register_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await update.message.reply_text("هذا الأمر يعمل فقط داخل القروبات.")
        return
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("يجب أن تكون admin لاستخدام هذا الأمر.")
        return
    existing = await get_group(chat.id)
    if existing:
        await update.message.reply_text(f"القروب مسجل أصلاً: {chat.title}")
    else:
        await add_group(chat_id=chat.id, title=chat.title)
        await update.message.reply_text(f"تم تسجيل القروب: {chat.title} ✓")


group_chat_member_handler = ChatMemberHandler(track_group_member, ChatMemberHandler.MY_CHAT_MEMBER)
group_new_members_handler = MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_group_new_members)
register_group_cmd = CommandHandler("registergroup", register_group_command)
