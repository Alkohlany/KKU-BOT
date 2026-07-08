from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler, MessageHandler, filters, CommandHandler
from bot.services.database import add_group, get_group
import logging

logger = logging.getLogger(__name__)


async def track_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.my_chat_member:
            return
        chat = update.my_chat_member.chat
        if not chat or chat.type not in ("group", "supergroup"):
            return
        new_status = update.my_chat_member.new_chat_member.status
        old_status = update.my_chat_member.old_chat_member.status
        is_member = new_status in ("member", "administrator", "creator")
        was_member = old_status in ("member", "administrator", "creator")
        bot_id = update.my_chat_member.new_chat_member.user.id if update.my_chat_member.new_chat_member.user else context.bot.id
        if not was_member and is_member and bot_id == context.bot.id:
            existing = await get_group(chat.id)
            if not existing:
                await add_group(chat_id=chat.id, title=chat.title)
                logger.info(f"Registered group via ChatMemberHandler: {chat.title} ({chat.id})")
    except Exception as e:
        logger.error(f"Error in track_group_member: {e}", exc_info=True)


async def track_group_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        logger.error(f"Error in track_group_new_members: {e}", exc_info=True)


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
