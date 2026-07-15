from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler, CommandHandler
from bot.services.database import add_channel_group, update_channel_group, get_channel_group_by_chat_id
import logging

logger = logging.getLogger(__name__)


async def track_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.my_chat_member:
            return

        chat = update.my_chat_member.chat
        new_status = update.my_chat_member.new_chat_member.status
        old_status = update.my_chat_member.old_chat_member.status

        if chat.type != "channel":
            return

        chat_id = chat.id
        title = chat.title or f"Channel {chat_id}"

        logger.info(f"Channel update: {title} ({chat_id}) - {old_status} -> {new_status}")

        if new_status in ("administrator", "member") and old_status in ("left", "kicked", "member"):
            existing = await get_channel_group_by_chat_id(chat_id)
            if not existing:
                member_count = 0
                invite_link = None
                try:
                    member_count = await context.bot.get_chat_member_count(chat_id)
                except Exception as e:
                    logger.warning(f"Could not get member count for {title}: {e}")
                try:
                    chat_info = await context.bot.get_chat(chat_id)
                    if chat_info.username:
                        invite_link = f"https://t.me/{chat_info.username}"
                    elif chat_info.invite_link:
                        invite_link = chat_info.invite_link
                except Exception as e:
                    logger.warning(f"Could not get chat info for {title}: {e}")
                await add_channel_group(chat_id, title, "channel", member_count, invite_link)
                logger.info(f"Registered channel: {title} ({chat_id}), members: {member_count}")
            else:
                logger.info(f"Channel already registered: {title} ({chat_id})")

        elif new_status in ("left", "kicked") and old_status in ("administrator", "member"):
            group = await get_channel_group_by_chat_id(chat_id)
            if group:
                await update_channel_group(group.id, is_active=False)
                logger.info(f"Deactivated channel: {title} ({chat_id})")
    except Exception as e:
        logger.error(f"Error in track_channel: {e}", exc_info=True)


async def register_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type != "channel":
        await update.message.reply_text("هذا الأمر يعمل فقط داخل القنوات.")
        return
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("يجب أن تكون admin لاستخدام هذا الأمر.")
        return
    existing_cg = await get_channel_group_by_chat_id(chat.id)
    if existing_cg:
        if not existing_cg.is_active:
            await update_channel_group(existing_cg.id, is_active=True)
            await update.message.reply_text(f"تم إعادة تفعيل القناة: {chat.title} ✓")
        else:
            await update.message.reply_text(f"القناة مسجلة أصلاً: {chat.title}")
    else:
        member_count = 0
        invite_link = None
        try:
            member_count = await context.bot.get_chat_member_count(chat.id)
        except Exception as e:
            logger.warning(f"Could not get member count: {e}")
        try:
            chat_info = await context.bot.get_chat(chat.id)
            if chat_info.username:
                invite_link = f"https://t.me/{chat_info.username}"
            elif chat_info.invite_link:
                invite_link = chat_info.invite_link
        except Exception as e:
            logger.warning(f"Could not get chat info: {e}")
        await add_channel_group(chat.id, chat.title, "channel", member_count, invite_link)
        await update.message.reply_text(f"تم تسجيل القناة: {chat.title} ✓\nعدد الأعضاء: {member_count}")


channel_chat_member_handler = ChatMemberHandler(track_channel, ChatMemberHandler.MY_CHAT_MEMBER)
register_channel_cmd = CommandHandler("registerchannel", register_channel_command)
