from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from bot.services.database import get_user, create_user, update_user_subscription, is_banned, get_official_channel
from bot.config import ADMIN_IDS
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

ANONYMOUS_ADMIN_ID = 1087968824
RATE_LIMIT = timedelta(seconds=5)

_last_api: dict[int, datetime] = {}
_last_result: dict[int, bool] = {}

_SUB_MSG = "• عذرآ يا {user_name}\n• عليك الاشتراك في قناه البوت للتمكن من التحدث هنا"


async def get_subscription_channel():
    """Get the single official subscription channel.

    Returns the active channel marked as official (type='channel',
    is_official=true, is_active=true). Returns None when no official
    channel is configured. Callers must handle None explicitly rather
    than assuming subscription is satisfied.
    """
    return await get_official_channel()


async def _ch_link_keyboard():
    channel = await get_subscription_channel()
    if not channel:
        return InlineKeyboardMarkup([[]])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("اضغط للاشتراك", url=channel.invite_link)
    ]])


async def verify_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channel = await get_subscription_channel()
    if not channel or user_id == ANONYMOUS_ADMIN_ID:
        return True

    now = datetime.utcnow()
    last = _last_api.get(user_id)

    if last and (now - last) < RATE_LIMIT:
        return _last_result.get(user_id, True)

    try:
        member = await context.bot.get_chat_member(chat_id=channel.chat_id, user_id=user_id)
        is_subscribed = member.status in ("member", "administrator", "creator")
        _last_api[user_id] = now
        _last_result[user_id] = is_subscribed
        await update_user_subscription(user_id, is_subscribed)
        return is_subscribed
    except Exception as e:
        logger.error(f"Subscription check error for user={user_id} channel={channel.chat_id}: {e}")
        return False


async def subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False
    if user.id == ANONYMOUS_ADMIN_ID:
        return True

    if await is_banned(user.id):
        await update.message.reply_text("❌ أنت محظور من استخدام البوت.")
        return False

    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(telegram_id=user.id, username=user.username, first_name=user.first_name)

    if not await verify_subscription(user.id, context):
        await update.message.reply_text(
            _SUB_MSG.format(user_name=user.first_name),
            reply_markup=await _ch_link_keyboard()
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
    if update.effective_user.id == ANONYMOUS_ADMIN_ID:
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

    if not await verify_subscription(user.id, context):
        try:
            await update.message.delete()
        except Exception:
            pass

        await update.effective_chat.send_message(
            _SUB_MSG.format(user_name=user.first_name),
            reply_markup=await _ch_link_keyboard()
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

    is_sub = await verify_subscription(user.id, context)
    await update_user_subscription(user.id, is_sub)

    try:
        await query.delete_message()
    except Exception:
        pass


check_subscription_handler = CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$")


async def global_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    # ponytail: تجاهل رسائل القناة المُعاد توجيهها للقروب
    if update.message.forward_from_chat or update.message.forward_from:
        return

    user = update.effective_user

    if user.id == context.bot.id:
        return
    if user.id == ANONYMOUS_ADMIN_ID:
        return
    if user.id in ADMIN_IDS:
        return
    if await is_banned(user.id):
        return

    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        try:
            member = await chat.get_member(user.id)
            if member.status in ("administrator", "creator"):
                return
        except Exception:
            return

    channel = await get_subscription_channel()
    if not channel:
        return

    if await verify_subscription(user.id, context):
        return

    if chat and chat.type == "private":
        await update.message.reply_text(
            _SUB_MSG.format(user_name=user.first_name),
            reply_markup=await _ch_link_keyboard()
        )
    else:
        try:
            await update.message.delete()
        except Exception:
            pass
        await chat.send_message(
            _SUB_MSG.format(user_name=user.first_name),
            reply_markup=await _ch_link_keyboard()
        )


global_subscription_handler = MessageHandler(
    filters.ALL & ~filters.ChatType.CHANNEL & ~filters.COMMAND & ~filters.StatusUpdate.NEW_CHAT_MEMBERS & ~filters.StatusUpdate.LEFT_CHAT_MEMBER,
    global_subscription_check
)
