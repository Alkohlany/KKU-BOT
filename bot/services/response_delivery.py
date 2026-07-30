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


def _is_specific_link(url: str) -> bool:
    """Return True if the link is a specific message link (https or t.me with message ID)."""
    return bool(re.search(r'https?://|t\.me/[a-zA-Z0-9_]+/\d+', url))


_LINK_RE = re.compile(r'(t\.me/[a-zA-Z0-9_]+/\d+|https?://[^\s<>"]+)')


def _extract_links_with_context(text: str) -> tuple[str, list[dict]]:
    """Extract all specific links and their labels from text.

    Returns:
        (cleaned_text, [{"label": "...", "url": "..."}, ...])
    """
    lines = text.split('\n')
    buttons: list[dict] = []
    cleaned_lines: list[str] = []

    for i, line in enumerate(lines):
        link_match = _LINK_RE.search(line)
        if link_match:
            url = link_match.group(1)
            if _is_specific_link(url):
                label = None
                text_before = line[:link_match.start()].strip().rstrip(':').rstrip('|-').strip()
                if text_before and len(text_before) > 2:
                    label = text_before
                elif i > 0 and not _LINK_RE.search(lines[i - 1]):
                    label = lines[i - 1].strip()
                if not label:
                    label = url.split('/')[-1]
                full_url = url if url.startswith('http') else f"https://{url}"
                buttons.append({"label": label, "url": full_url})
                continue
        cleaned_lines.append(line)

    if len(buttons) == 1:
        buttons[0]["label"] = "🔗 اضغط هنا"

    cleaned_text = '\n'.join(cleaned_lines).strip()
    return cleaned_text, buttons


def _build_url_keyboard(buttons: list[dict], existing_markup=None) -> InlineKeyboardMarkup | None:
    """Build an InlineKeyboardMarkup from a list of buttons."""
    rows = []
    for btn in buttons:
        rows.append([InlineKeyboardButton(text=btn["label"], url=btn["url"])])
    if existing_markup and hasattr(existing_markup, 'inline_keyboard'):
        rows.extend(existing_markup.inline_keyboard)
    return InlineKeyboardMarkup(rows) if rows else None


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
                cleaned, link_buttons = _extract_links_with_context(content)
                markup = _build_url_keyboard(link_buttons, reply_markup)
                if news_post.image_url:
                    await message.reply_photo(
                        photo=news_post.image_url,
                        caption=cleaned,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                elif news_post.file_url:
                    await message.reply_document(
                        document=news_post.file_url,
                        caption=cleaned,
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                else:
                    await message.reply_text(
                        cleaned,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=markup,
                    )
                return True

        if not getattr(response, "response", None) and not getattr(response, "file_tg_id", None) and not getattr(response, "file_url", None):
            return False

        caption = _with_prefix(getattr(response, "response", None), prefix, response)
        caption = wrap_links_in_blockquote(caption) if caption else None
        cleaned, link_buttons = _extract_links_with_context(caption or "")
        display = cleaned if link_buttons else caption
        markup = _build_url_keyboard(link_buttons, reply_markup)

        file_tg_id = getattr(response, "file_tg_id", None)
        file_url = getattr(response, "file_url", None)
        file_type = getattr(response, "file_type", None)

        if file_tg_id:
            if file_type == "photo":
                await message.reply_photo(photo=file_tg_id, caption=display, parse_mode="HTML", reply_markup=markup)
            elif file_type == "video":
                await message.reply_video(video=file_tg_id, caption=display, parse_mode="HTML", reply_markup=markup)
            else:
                await message.reply_document(document=file_tg_id, caption=display, parse_mode="HTML", reply_markup=markup)
            return True

        if file_url:
            if file_type == "photo":
                await message.reply_photo(photo=file_url, caption=display, parse_mode="HTML", reply_markup=markup)
            elif file_type == "video":
                await message.reply_video(video=file_url, caption=display, parse_mode="HTML", reply_markup=markup)
            else:
                await message.reply_document(document=file_url, caption=display, parse_mode="HTML", reply_markup=markup)
            return True

        await message.reply_text(
            display or "",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup,
        )
        return True
    except Exception as exc:
        logger.warning("Could not send selected auto response %s: %s", getattr(response, "id", None), exc)
        return False
