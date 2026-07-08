from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler
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
                await add_channel_group(chat_id, title, "channel")
                logger.info(f"Registered channel: {title} ({chat_id})")
            else:
                logger.info(f"Channel already registered: {title} ({chat_id})")

        elif new_status in ("left", "kicked") and old_status in ("administrator", "member"):
            group = await get_channel_group_by_chat_id(chat_id)
            if group:
                await update_channel_group(group.id, is_active=False)
                logger.info(f"Deactivated channel: {title} ({chat_id})")
    except Exception as e:
        logger.error(f"Error in track_channel: {e}", exc_info=True)


channel_chat_member_handler = ChatMemberHandler(track_channel, ChatMemberHandler.MY_CHAT_MEMBER)
