from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler, MessageHandler, filters, CommandHandler
from bot.services.database import add_channel_group, get_channel_group_by_chat_id, update_channel_group, get_setting
import logging

logger = logging.getLogger(__name__)


async def track_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.my_chat_member:
            return
        chat = update.my_chat_member.chat
        if not chat:
            return

        new_status = update.my_chat_member.new_chat_member.status
        old_status = update.my_chat_member.old_chat_member.status

        if chat.type == "channel":
            chat_type = "channel"
        elif chat.type in ("group", "supergroup"):
            chat_type = "group"
        else:
            return

        is_member = new_status in ("member", "administrator", "creator")
        was_member = old_status in ("member", "administrator", "creator")
        bot_id = update.my_chat_member.new_chat_member.user.id if update.my_chat_member.new_chat_member.user else context.bot.id

        if not was_member and is_member and bot_id == context.bot.id:
            existing = await get_channel_group_by_chat_id(chat.id)
            if not existing:
                # Fetch member count and channel/group link from Telegram API
                member_count = 0
                invite_link = None
                try:
                    member_count = await context.bot.get_chat_member_count(chat.id)
                except Exception as e:
                    logger.warning(f"Could not get member count for {chat.title}: {e}")
                try:
                    chat_info = await context.bot.get_chat(chat.id)
                    if chat_info.username:
                        invite_link = f"https://t.me/{chat_info.username}"
                    elif chat_info.invite_link:
                        invite_link = chat_info.invite_link
                except Exception as e:
                    logger.warning(f"Could not get chat info for {chat.title}: {e}")
                
                await add_channel_group(chat.id, chat.title, chat_type, member_count, invite_link)
                logger.info(f"Registered {chat_type}: {chat.title} ({chat.id}), members: {member_count}")
            else:
                logger.info(f"{chat_type} already registered: {chat.title} ({chat.id})")
        elif was_member and not is_member and bot_id == context.bot.id:
            existing = await get_channel_group_by_chat_id(chat.id)
            if existing:
                await update_channel_group(existing.id, is_active=False)
                logger.info(f"Deactivated {chat_type}: {chat.title} ({chat.id})")
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
                existing = await get_channel_group_by_chat_id(chat.id)
                if not existing:
                    # Fetch member count and channel/group link
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
                    
                    await add_channel_group(chat.id, chat.title, "group", member_count, invite_link)
                    logger.info(f"Registered group via NEW_CHAT_MEMBERS: {chat.title} ({chat.id}), members: {member_count}")
            else:
                auto_greeting = await get_setting("autoGreeting")
                if auto_greeting == "false":
                    continue
                welcome_msg = await get_setting("welcomeMessage")
                if not welcome_msg:
                    welcome_msg = "مرحباً بك في مجموعة الجامعة! 👋"
                try:
                    await chat.send_message(f"مرحباً {member.first_name}! {welcome_msg}")
                except Exception as e:
                    logger.warning(f"Could not send welcome message: {e}")
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
    existing_cg = await get_channel_group_by_chat_id(chat.id)
    if existing_cg:
        await update.message.reply_text(f"القروب مسجل أصلاً: {chat.title}")
    else:
        # Fetch member count and channel/group link
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
        
        await add_channel_group(chat.id, chat.title, "group", member_count, invite_link)
        await update.message.reply_text(f"تم تسجيل القروب: {chat.title} ✓\nعدد الأعضاء: {member_count}")


async def edit_chat_title(chat_id, new_title, context):
    """Edit the channel/group title on Telegram"""
    try:
        await context.bot.set_chat_title(chat_id, new_title)
        return True
    except Exception as e:
        logger.error(f"Could not edit chat title: {e}")
        return False


group_chat_member_handler = ChatMemberHandler(track_group_member, ChatMemberHandler.MY_CHAT_MEMBER)
group_new_members_handler = MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_group_new_members)
register_group_cmd = CommandHandler("registergroup", register_group_command)
