from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.services.database import get_user, create_user, update_user_subscription, is_banned
from bot.config import CHANNEL_ID, CHANNEL_LINK
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        if "Member list is inaccessible" in str(e) or "chat_admin_required" in str(e):
            logger.warning(f"Cannot check subscription: {e}. Allowing user.")
            return True
        logger.error(f"Error checking subscription: {e}")
        return False


async def subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False

    if await is_banned(user.id):
        await update.message.reply_text("❌ أنت محظور من استخدام البوت.")
        return False

    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

    from datetime import datetime
    now = datetime.utcnow()
    
    if db_user.last_check:
        time_since_check = now - db_user.last_check
        if db_user.is_subscribed and time_since_check < timedelta(hours=6):
            return True
        elif time_since_check >= timedelta(hours=6):
            is_subscribed = await check_subscription(user.id, context)
            await update_user_subscription(user.id, is_subscribed)
            if not is_subscribed:
                keyboard = [[
                    InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK),
                    InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
                ]]
                markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"📢 لاستخدام البوت، يجب الاشتراك في القناة أولاً\n\n"
                    f"🔗 الاشتراك هنا: {CHANNEL_LINK}",
                    reply_markup=markup
                )
                return False
            return True
    
    if db_user.is_subscribed:
        return True

    is_subscribed = await check_subscription(user.id, context)
    await update_user_subscription(user.id, is_subscribed)

    if not is_subscribed:
        keyboard = [[
            InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK),
            InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
        ]]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📢 لاستخدام البوت، يجب الاشتراك في القناة أولاً\n\n"
            f"🔗 الاشتراك هنا: {CHANNEL_LINK}",
            reply_markup=markup
        )
        return False

    return True


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if not user:
        return

    is_subscribed = await check_subscription(user.id, context)
    await update_user_subscription(user.id, is_subscribed)

    if is_subscribed:
        chat_type = update.effective_chat.type
        if chat_type in ["group", "supergroup"]:
            await query.edit_message_text("✅ تم التحقق من اشتراكك بنجاح")
        else:
            from bot.handlers.start import START_MESSAGE, FEATURES_KEYBOARD
            await query.edit_message_text(
                "✅ تم التحقق من اشتراكك بنجاح! يمكنك استخدام البوت الآن."
            )
            await query.message.reply_text(START_MESSAGE, reply_markup=InlineKeyboardMarkup(FEATURES_KEYBOARD))
    else:
        chat_type = update.effective_chat.type
        if chat_type in ["group", "supergroup"]:
            await query.edit_message_text(
                "❌ أنت غير مشترك في القناة بعد.\n\n"
                f"🔗 الاشتراك هنا: {CHANNEL_LINK}"
            )
        else:
            keyboard = [[
                InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK),
                InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
            ]]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ أنت غير مشترك في القناة بعد.\n\n"
                f"🔗 الاشتراك هنا: {CHANNEL_LINK}\n"
                "بعد الاشتراك، اضغط على زر التحقق.",
                reply_markup=markup
            )


check_subscription_handler = CallbackQueryHandler(
    check_subscription_callback,
    pattern="^check_subscription$"
)
