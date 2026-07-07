from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from bot.services.database import get_user, create_user, update_user_subscription, is_banned
from bot.config import CHANNEL_ID, CHANNEL_LINK
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

MEMO_TTL = timedelta(minutes=30)
DB_TTL = timedelta(hours=1)
API_TTL = timedelta(hours=6)

_memo: dict[int, tuple[bool, datetime]] = {}


def _memo_get(user_id: int) -> bool | None:
    entry = _memo.get(user_id)
    if entry and (datetime.utcnow() - entry[1]) < MEMO_TTL:
        return entry[0]
    return None


def _memo_set(user_id: int, value: bool):
    _memo[user_id] = (value, datetime.utcnow())


def _sub_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK),
        InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
    ]])


async def verify_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE, force_api: bool = False) -> bool:
    cached = _memo_get(user_id)
    if cached is not None and not force_api:
        return cached

    db_user = await get_user(user_id)
    now = datetime.utcnow()

    if db_user and db_user.last_check and not force_api:
        age = now - db_user.last_check
        if db_user.is_subscribed and age < DB_TTL:
            _memo_set(user_id, True)
            return True
        if not db_user.is_subscribed and age < API_TTL:
            _memo_set(user_id, False)
            return False

    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        is_sub = member.status in ("member", "administrator", "creator")
    except Exception as e:
        if "MEMBER_LIST_INACCESSIBLE" in str(e) or "chat_admin_required" in str(e) or "member list is inaccessible" in str(e).lower():
            logger.warning(f"Cannot check subscription for {user_id}, allowing: {e}")
            return True
        logger.error(f"Subscription check error for {user_id}: {e}")
        is_sub = False

    _memo_set(user_id, is_sub)
    await update_user_subscription(user_id, is_sub)
    return is_sub


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

    is_sub = await verify_subscription(user.id, context)

    if not is_sub:
        await update.message.reply_text(
            f"📢 لاستخدام البوت، يجب الاشتراك في القناة أولاً\n\n🔗 الاشتراك هنا: {CHANNEL_LINK}",
            reply_markup=_sub_keyboard()
        )
    return is_sub


async def group_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    user = update.effective_user
    if not user:
        return

    try:
        member = await chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        return

    if user.id == context.bot.id:
        return
    if await is_banned(user.id):
        return

    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(telegram_id=user.id, username=user.username, first_name=user.first_name)

    is_sub = await verify_subscription(user.id, context)

    if not is_sub and update.message.text:
        try:
            await update.message.delete()
        except Exception:
            pass

        await chat.send_message(
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

    is_sub = await verify_subscription(user.id, context, force_api=True)
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
