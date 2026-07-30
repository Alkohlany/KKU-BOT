"""إرسال الرد المختار مع دعم الملفات والمنشورات المرتبطة."""

from __future__ import annotations

import logging
import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.services.database import get_news_by_id
from bot.services.news_publisher import wrap_links_in_blockquote
from bot.services.response_engine import needs_freshness_warning

logger = logging.getLogger(__name__)


def _extract_url(text: str) -> str | None:
    match = re.search(r'(https?://[^\s<>"]+|t\.me/[^\s<>"]+/\d+)', text or "")
    return match.group(0) if match else None


def _url_button_markup(content: str, base_markup=None) -> InlineKeyboardMarkup | None:
    url = _extract_url(content)
    if not url:
        return base_markup
    button = InlineKeyboardButton("🔗 افتح الرابط", url=url)
    if base_markup and hasattr(base_markup, "inline_keyboard"):
        rows = [list(row) for row in base_markup.inline_keyboard]
        rows.append([button])
        return InlineKeyboardMarkup(rows)
    return InlineKeyboardMarkup([[button]])


FRESHNESS_WARNING = (
    "ℹ️ <b>تنبيه:</b> هذا المحتوى مرتبط بموعد أو فترة زمنية؛ "
    "تحقق من تاريخ المنشور قبل الاعتماد عليه."
)


def _with_prefix(content: str | None, prefix: str | None, response: Any) -> str | None:
    parts: list[str] = []
    if prefix:
        parts.append(prefix.strip())
    if needs_freshness_warning(response):
        parts.append(FRESHNESS_WARNING)
    if content:
        parts.append(content.strip())
    return "\n\n".join(part for part in parts if part) or None


async def send_auto_response(
    message: Message,
    response: Any,
    *,
    prefix: str | None = None,
    reply_markup=None,
) -> bool:
    """يرسل AutoResponse ويعيد True عند النجاح."""
    try:
        if getattr(response, "news_id", None):
            news_post = await get_news_by_id(response.news_id)
            if news_post:
                content = _with_prefix(news_post.content or "", prefix, response) or ""
                content = wrap_links_in_blockquote(content)
                markup = _url_button_markup(content, reply_markup)
                if news_post.image_url:
                    await message.reply_photo(
                        photo=news_post.image_url,
                        caption=content,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                elif news_post.file_url:
                    await message.reply_document(
                        document=news_post.file_url,
                        caption=content,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                else:
                    await message.reply_text(
                        content,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=markup,
                    )
                return True

        if not getattr(response, "response", None) and not getattr(response, "file_tg_id", None) and not getattr(response, "file_url", None):
            return False

        caption = _with_prefix(getattr(response, "response", None), prefix, response)
        caption = wrap_links_in_blockquote(caption) if caption else None
        markup = _url_button_markup(caption or "", reply_markup)

        file_tg_id = getattr(response, "file_tg_id", None)
        file_url = getattr(response, "file_url", None)
        file_type = getattr(response, "file_type", None)

        if file_tg_id:
            if file_type == "photo":
                await message.reply_photo(photo=file_tg_id, caption=caption, parse_mode="HTML", reply_markup=markup)
            elif file_type == "video":
                await message.reply_video(video=file_tg_id, caption=caption, parse_mode="HTML", reply_markup=markup)
            else:
                await message.reply_document(document=file_tg_id, caption=caption, parse_mode="HTML", reply_markup=markup)
            return True

        if file_url:
            if file_type == "photo":
                await message.reply_photo(photo=file_url, caption=caption, parse_mode="HTML", reply_markup=markup)
            elif file_type == "video":
                await message.reply_video(video=file_url, caption=caption, parse_mode="HTML", reply_markup=markup)
            else:
                await message.reply_document(document=file_url, caption=caption, parse_mode="HTML", reply_markup=markup)
            return True

        await message.reply_text(
            caption or "",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup,
        )
        return True
    except Exception as exc:
        logger.warning("Could not send selected auto response %s: %s", getattr(response, "id", None), exc)
        return False
