from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from bot.services.database import get_user, create_user, update_user_subscription, is_banned
from bot.config import CHANNEL_ID, CHANNEL_LINK
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

CACHE_SUBSCRIBED = timedelta(minutes=10)
CACHE_UNSUBSCRIBED = timedelta(minutes=2)


def _sub_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK),
        InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
    ]])


async def _api_check(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        if "member list is inaccessible" in str(e).lower() or "chat_admin_required" in str(e):
            logger.warning(f"Cannot check subscription for {user_id}, allowing: {e}")
            return True
        logger.error(f"Subscription check error for {user_id}: {e}")
        return False


async def verify_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    db_user = await get_user(user_id)
    now = datetime.utcnow()

    if db_user and db_user.last_check:
        age = now - db_user.last_check
        ttl = CACHE_SUBSCRIBED if db_user.is_subscribed else CACHE_UNSUBSCRIBED
        if age < ttl:
            return db_user.is_subscribed

    is_subscribed = await _api_check(user_id, context)
    await update_user_subscription(user_id, is_subscribed)
    return is_subscribed


async def subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False

    if await is_banned(user.id):
        await update.message.reply_text("❌ أنت محظور من استخدام البوت.")
        return False

    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(telegram_id=user.id, username=user.username, first_name=user.first_name)

    if not await verify_subscription(user.id, context):
        await update.message.reply_text(
            f"📢 لاستخدام البوت، يجب الاشتراك في القناة أولاً\n\n🔗 الاشتراك هنا: {CHANNEL_LINK}",
            reply_markup=_sub_keyboard()
        )
        return False
    return True


async def group_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    if update.effective_user.id == context.bot.id:
        return
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        return
    if await is_banned(update.effective_user.id):
        return

    user = update.effective_user
    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(telegram_id=user.id, username=user.username, first_name=user.first_name)

    now = datetime.utcnow()
    if db_user.last_check:
        age = now - db_user.last_check
        if db_user.is_subscribed and age < CACHE_SUBSCRIBED:
            return
        if not db_user.is_subscribed and age < CACHE_UNSUBSCRIBED:
            return

    if await verify_subscription(user.id, context):
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message(
        f"📢 {user.first_name}، لاستخدام البوت يجب الاشتراك في القناة أولاً\n\n🔗 الاشتراك هنا: {CHANNEL_LINK}",
        reply_markup=_sub_keyboard()
    )


group_subscription_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
    group_subscription_check
)


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if not user:
        return

    is_sub = await _api_check(user.id, context)
    await update_user_subscription(user.id, is_sub)
    chat_type = update.effective_chat.type

    if is_sub:
        msg = "✅ تم التحقق من اشتراكك بنجاح"
        if chat_type not in ("group", "supergroup"):
            from bot.handlers.start import START_MESSAGE, FEATURES_KEYBOARD
            await query.edit_message_text(msg)
            await query.message.reply_text(START_MESSAGE, reply_markup=InlineKeyboardMarkup(FEATURES_KEYBOARD))
        else:
            await query.edit_message_text(msg)
    else:
        msg = f"❌ أنت غير مشترك في القناة بعد.\n\n🔗 الاشتراك هنا: {CHANNEL_LINK}"
        if chat_type not in ("group", "supergroup"):
            await query.edit_message_text(msg, reply_markup=_sub_keyboard())
        else:
            await query.edit_message_text(msg)


check_subscription_handler = CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$")
