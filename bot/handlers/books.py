from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from bot.middleware.subscription import subscription_required
from bot.services.database import get_all_book_groups, get_active_channel_groups, get_official_channel
from bot.services.news_publisher import wrap_links_in_blockquote
from bot.config import normalize_arabic
import logging
import re

logger = logging.getLogger(__name__)

_BOOK_REQUEST_RE = re.compile(
    r"(?:^|\s)(?:الكتب|الكتاب|كتب|كتاب)"
    r"(?:\s+.*)?\s*[؟?]?\s*$"
)

_SPECIALTY_REQUEST_RE = re.compile(
    r"(?:تسريبات|حلول|تجميعات|ملخصات|شروحات| exam|mid|final)"
    r".*(?:كتب|كتاب|material|resources)?",
    re.IGNORECASE
)


def is_book_request(text: str) -> bool:
    """يكتشف طلبات الكتب مثل 'كتب الطب' أو 'وين الاقي كتب التسريبات' أو 'تسريبات التحصيلي'."""
    normalized = normalize_arabic((text or "").lower()).strip()
    return bool(_BOOK_REQUEST_RE.search(normalized) or _SPECIALTY_REQUEST_RE.search(normalized))


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type in ['group', 'supergroup']:
        bot_username = context.bot.username
        await update.message.reply_text(
            f"🟢 هنا الكتب المتوفرة جامعة الملك خالد\n\n"
            f"https://t.me/{bot_username}?start=books", disable_web_page_preview=True)
        return

    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    text = await get_books_text()
    await update.message.reply_text(wrap_links_in_blockquote(text), parse_mode='HTML', disable_web_page_preview=True)


async def get_books_text() -> str:
    groups = await get_all_book_groups()
    groups = [g for g in groups if g.is_active]

    if not groups:
        return "لا توجد كتب منشورة حالياً 📭"

    channel = await get_official_channel()
    if not channel:
        all_channels = await get_active_channel_groups()
        for ch in all_channels:
            if ch.type == 'channel':
                channel = ch
                break

    channel_username = None
    if channel and channel.invite_link and 't.me/' in channel.invite_link:
        channel_username = channel.invite_link.split('t.me/')[-1].strip('/')

    text = "📚 الكتب المتوفرة\n"
    text += "جامعة الملك خالد\n\n"

    for group in groups:
        if group.channel_message_id and channel_username:
            group_link = f"https://t.me/{channel_username}/{group.channel_message_id}"
            text += f"{group.title} 🔻\n{group_link}\n\n"
        else:
            text += f"{group.title} 🔻\n"

    text += "🔴 انضموا لقروب جامعة الملك خالد العام 🔻\n"
    text += "https://t.me/KKU_Main1\n\n"
    text += "🟠 انضموا لقروب الواتساب العام 🔻\n"
    text += "https://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n"
    text += "#شاركها_فربما_يبحث_عنها_غيرك"

    return text


async def books_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ponytail: تجاهل رسائل القناة المُعاد توجيهها
    if update.message.forward_from_chat or update.message.forward_from:
        return
    await books_command(update, context)


books_handler = CommandHandler("books", books_command)
books_text_handler = MessageHandler(
    filters.Regex(r"(?:^|\s)(?:الكتب|الكتاب|كتب|كتاب)(?:\s+.*)?\s*[؟?]?\s*$") |
    filters.Regex(r"(?:تسريبات|حلول|تجميعات|ملخصات|شروحات|exam|mid|final)"),
    books_text_command
)
