"""Advanced protection system for KKU Bot groups."""

import re
import logging
import unicodedata
import asyncio
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.services.database import is_banned, ban_user, log_activity, get_channel_group_by_chat_id, get_setting
from bot.services.ai import _call_model

logger = logging.getLogger(__name__)

SPAM_KEYWORDS = [
    # روابط مختصرة
    "taplink", "linktr", "bit.ly", "tinyurl",
    "cutt.ly", "shorturl.at", "rb.gy", "is.gd", "ow.ly",
    # محتوى إباحي
    "xxx", "porn", "porno",
    "محتوى اباحي", "إباحي", "إباحية",
    # مخدرات
    "مخدر", "مخدرات", "حشيش", "بانجو",
    "drugs", "cannabis", "marijuana",
    # نصب
    "احتيال", "خديعة",
    "scam", "fraud",
    # خدمات مشبوهة
    "سكليف", "اجازة مرضية", "تقرير طبي", "شهادة صحيه", "حذف ملاحظة",
    # كلمات تجارية مشبوهة
    "للبيع", "رابط واتساب", "رقم واتساب", "رابط تيليجرام", "يتوفر مكان",
]

SUSPICIOUS_PATTERNS = [
    r"(https?://\S+){3,}",
    r"@[\w+]{15,}",
    r"https?://\S*(?:wa\.me|whatsapp|chat\.whatsapp|t\.me|joinchat)\S*",
    r"(?:^|\s)(?:\+?967)?[71]\d{7}(?:\s|$)",
    r"(?:^|\s)05\d{8}(?:\s|$)",
    r"\+\d{10,}",
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


_ai_cache: dict[str, tuple[bool, float]] = {}
_AI_CACHE_TTL = 60

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


async def check_with_ai(text: str) -> bool:
    cache_key = hashlib.md5(text.encode()).hexdigest()
    now = datetime.now().timestamp()
    cached = _ai_cache.get(cache_key)
    if cached and (now - cached[1]) < _AI_CACHE_TTL:
        return cached[0]

    prompt = f"""هل هذه الرسالة إعلان تجاري أو ترويجي؟
الرسالة: "{text}"
أجب بكلمة واحدة فقط: نعم أو لا."""

    try:
        response = await asyncio.to_thread(_call_model, prompt)
        response = response.strip().lower()
        result = "نعم" in response or "yes" in response
    except Exception:
        return False

    _ai_cache[cache_key] = (result, now)
    return result


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
    keyword_match = None
    pattern_match = None

    for keyword in SPAM_KEYWORDS:
        normalized_keyword = normalize_arabic(keyword.lower())
        if normalized_keyword in normalized:
            keyword_match = keyword
            break

    if not keyword_match:
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, text):
                pattern_match = pattern
                break

    if keyword_match or pattern_match:
        reason = f"Spam keyword: {keyword_match}" if keyword_match else f"Suspicious pattern: {pattern_match}"
        detail = keyword_match or pattern_match
        if await check_with_ai(text):
            await _ban_user(update, context, user, chat, reason, "ai_confirmed_spam", detail)
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
