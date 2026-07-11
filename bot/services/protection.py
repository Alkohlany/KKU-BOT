"""Advanced protection system for KKU Bot groups."""

import re
import logging
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.services.database import is_banned, ban_user, log_activity, get_channel_group_by_chat_id, get_setting

logger = logging.getLogger(__name__)

SPAM_KEYWORDS = [
    # تسويق/إعلان
    "خصم", "توصيل",
    "إعلان", "إعلانات", "تسويق", "ربح", "دخل",
    "taplink", "linktr", "bit.ly", "tinyurl",
    "casino", "bet", "gambling",
    # محتوى إباحي
    "عري", "عارية",
    "sex", "sexy", "nude", "naked",
    "xxx", "porn", "porno",
    "محتوى اباحي", "إباحي", "إباحية",
    # كراهية
    "كافر", "كافرين", "مرتد", "مرتدين", "ملحد", "ملحدين",
    "يهودي", "يهود", "نصراني", "نصارى",
    "طائفي", "طائفية", "sectarian",
    # مخدرات
    "مخدر", "مخدرات", "حشيش", "بانجو",
    "drugs", "cannabis", "marijuana",
    # نصب
    "نصب", "احتيال", "غش", "خديعة",
    "scam", "fraud", "hack", "hacking",
    "احصل على", "free money",
]

SUSPICIOUS_PATTERNS = [
    r"(https?://\S+){3,}",
    r"@[\w+]{15,}",
    r"\+?\d{10,}",
]


def normalize_arabic(text):
    """تطبيع النص العربي لمنع التجاوز"""
    text = unicodedata.normalize("NFKD", text)
    # إزالة الحركات
    for ch in ("ً", "ٌ", "ٍ", "َ", "ُ", "ِ", "ّ", "ْ"):
        text = text.replace(ch, "")
    # استبدال الأحرف المشابهة
    replacements = {
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


user_message_times = defaultdict(list)


async def _ban_user(update, context, user, chat, reason: str, log_action: str, log_detail: str):
    if await _is_privileged(user.id, chat):
        return
    try:
        await update.message.delete()
        await chat.ban_member(user.id)
        await ban_user(user.id, reason, context.bot.id)
        await log_activity(log_action, f"{reason} from {user.id} in {chat.id}", user.id)
        await chat.send_message(f"تم حظر المستخدم {user.first_name} بسبب محتوى مخالف.")
        log_protection(user.id, chat.id, log_action, log_detail)
    except Exception as e:
        logger.error(f"Error banning user {user.id}: {e}")


def is_rate_limited(user_id, max_messages=None, time_window=None):
    """فحص Rate Limiting"""
    if max_messages is None:
        max_messages = 5
    if time_window is None:
        time_window = 60
    now = datetime.now()
    user_times = user_message_times[user_id]
    user_times[:] = [t for t in user_times if now - t < timedelta(seconds=time_window)]
    if len(user_times) >= max_messages:
        return True
    user_times.append(now)
    return False


def log_protection(user_id, chat_id, reason, detail):
    """تسجيل الحماية"""
    logger.warning(
        f"PROTECTION: user={user_id} chat={chat_id} reason={reason} detail={detail}"
    )


async def _is_privileged(user_id: int, chat) -> bool:
    try:
        member = await chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def check_text_content(update, context, text):
    """فحص النص (مستخدمة في الرسائل النصية والوسائط)"""
    user = update.effective_user
    chat = update.effective_chat

    if await _is_privileged(user.id, chat):
        return

    anti_spam = await get_setting("antiSpam")
    if anti_spam == "false":
        return

    normalized = normalize_arabic(text.lower())

    for keyword in SPAM_KEYWORDS:
        if keyword.lower() in normalized:
            await _ban_user(update, context, user, chat, f"Spam keyword: {keyword}", "spam_keyword", keyword)
            return

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text):
            await _ban_user(update, context, user, chat, f"Suspicious pattern: {pattern}", "suspicious_pattern", pattern)
            return


async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الرسائل النصية"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    if user.id == context.bot.id:
        return

    if chat.type not in ["group", "supergroup"]:
        return

    try:
        member = await chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception as e:
        logger.warning(f"Cannot check member status for {user.id}, allowing: {e}")
        return

    try:
        group = await get_channel_group_by_chat_id(chat.id)
        if not group or not group.is_active:
            return
    except Exception as e:
        logger.error(f"Error checking group status: {e}")

    try:
        if await is_banned(user.id):
            try:
                await update.message.delete()
                await chat.ban_member(user.id)
                await log_activity(
                    "spam_delete",
                    f"Deleted message from banned user {user.id} in {chat.id}",
                    user.id,
                )
            except Exception as e:
                logger.error(f"Error handling banned user: {e}")
            return
    except Exception as e:
        logger.error(f"Database error checking ban status: {e}")
        return

    anti_flood = await get_setting("antiFlood")
    if anti_flood != "false":
        flood_limit = int(await get_setting("floodLimit") or "5")
        flood_time = int(await get_setting("floodTime") or "60")
        if is_rate_limited(user.id, max_messages=flood_limit, time_window=flood_time):
            if await _is_privileged(user.id, chat):
                return
            await _ban_user(update, context, user, chat, "Rate limit exceeded", "rate_limit", "exceeded")
            return

    await check_text_content(update, context, update.message.text)


async def check_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الوسائط (صور/فيديو/ملفات)"""
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    if update.effective_chat.type not in ("group", "supergroup"):
        return
    if update.effective_user.id == context.bot.id:
        return
    if await _is_privileged(update.effective_user.id, update.effective_chat):
        return

    caption = update.message.caption or ""
    if not caption:
        return

    await check_text_content(update, context, caption)


protection_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND, check_message
)

protection_media_handler = MessageHandler(
    (filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.ANIMATION)
    & ~filters.COMMAND,
    check_media,
)
