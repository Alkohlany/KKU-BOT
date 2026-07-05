"""Advanced protection system for KKU Bot groups."""

import re
import logging
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.services.database import is_banned, ban_user, log_activity, get_group

logger = logging.getLogger(__name__)

SPAM_KEYWORDS = [
    # تسويق/إعلان
    "اشترك", "اشتراك", "عرض", "خصم", "توصيل", "شحن",
    "إعلان", "إعلانات", "تسويق", "ربح", "دخل",
    "taplink", "linktr", "bit.ly", "tinyurl",
    "casino", "bet", "gambling",
    # محتوى إباحي/استغلال
    "اطفال", "طفل", "اطفالي", "infant", "child", "children",
    "فيديوهات", "فيديو", "ساخن", "ساخنة", "عري", "عاري", "عارية",
    "hot video", "hot videos", "sex", "sexy", "nude", "naked",
    "adult", "xxx", "porn", "porno",
    "محتوى اباحي", "فاضح", "فاضحة", "إباحي", "إباحية",
    # عنصري/كراهية
    "كافر", "كافرين", "مرتد", "مرتدين", "ملحد", "ملحدين",
    "يهودي", "يهود", "نصراني", "نصارى",
    "طائفي", "طائفية", "sectarian",
    # مخدرات/أسلحة
    "مخدر", "مخدرات", "حشيش", "بانجو", "كيف",
    "drugs", "drug", "cannabis", "marijuana",
    "سلاح", "أسلحة", "ذخيرة", "متفجر",
    # نصب/احتيال
    "نصب", "احتيال", "غش", "خديعة",
    "scam", "fraud", "fake", "hack", "hacking",
    "احصل على", "مجاناً", "grabs", "free money",
]

SUSPICIOUS_PATTERNS = [
    r"(https?://\S+){3,}",
    r"@[\w+]{15,}",
    r"\+?\d{10,}",
    r"t\.me/",
    r"telegram\.me/",
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


def is_rate_limited(user_id, max_messages=5, time_window=60):
    """فحص Rate Limiting"""
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


async def check_text_content(update, context, text):
    """فحص النص (مستخدمة في الرسائل النصية والوسائط)"""
    user = update.effective_user
    chat = update.effective_chat

    normalized = normalize_arabic(text.lower())

    for keyword in SPAM_KEYWORDS:
        if keyword.lower() in normalized:
            try:
                await update.message.delete()
                await chat.ban_member(user.id)
                await ban_user(user.id, f"Spam keyword: {keyword}", context.bot.id)
                await log_activity(
                    "spam_detected",
                    f"Keyword '{keyword}' detected from {user.id} in {chat.id}",
                    user.id,
                )
                await chat.send_message(
                    f"تم حظر المستخدم {user.first_name} بسبب محتوى مخالف."
                )
                log_protection(user.id, chat.id, "spam_keyword", keyword)
            except Exception as e:
                logger.error(f"Error banning spammer: {e}")
            return

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text):
            try:
                await update.message.delete()
                await chat.ban_member(user.id)
                await ban_user(user.id, f"Suspicious pattern: {pattern}", context.bot.id)
                await log_activity(
                    "suspicious_message",
                    f"Suspicious pattern '{pattern}' from {user.id} in {chat.id}",
                    user.id,
                )
                log_protection(user.id, chat.id, "suspicious_pattern", pattern)
            except Exception as e:
                logger.error(f"Error handling suspicious message: {e}")
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
        if member.status in ["administrator", "creator"]:
            return
    except Exception as e:
        logger.error(f"Error checking member status: {e}")

    try:
        group = await get_group(chat.id)
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

    if is_rate_limited(user.id):
        try:
            await update.message.delete()
            await chat.ban_member(user.id)
            await ban_user(user.id, "Rate limit exceeded", context.bot.id)
            await log_activity(
                "rate_limit",
                f"Rate limit exceeded by {user.id} in {chat.id}",
                user.id,
            )
            log_protection(user.id, chat.id, "rate_limit", "exceeded")
        except Exception as e:
            logger.error(f"Error handling rate limit: {e}")
        return

    await check_text_content(update, context, update.message.text)


async def check_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الوسائط (صور/فيديو/ملفات)"""
    if not update.message:
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
