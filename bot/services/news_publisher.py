import logging
import re
from telegram import Bot
from bot.services.database import get_all_groups
from bot.config import BOT_TOKEN, CHANNEL_ID
from bot.services.cloud_storage import download_raw
import asyncio
import httpx
import os

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)


def wrap_links_in_blockquote(text: str) -> str:
    """Wrap URLs in text with <blockquote> tags"""
    url_pattern = r'(https?://[^\s<]+|t\.me/[^\s<]+|www\.[^\s<]+)'
    def replace_url(match):
        url = match.group(0)
        return f'<blockquote>{url}</blockquote>'
    return re.sub(url_pattern, replace_url, text)


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, file_id: str = None, to_groups: bool = True, to_channel: bool = False, as_document: bool = False, file_name: str = None, thumbnail_url: str = None) -> tuple[int, int | None]:
    text = wrap_links_in_blockquote(text)
    groups = await get_all_groups()
    sent = 0
    channel_message_id = None

    if to_groups:
        for group in groups:
            if not group.is_active:
                continue
            try:
                if await _send_to_chat(str(group.chat_id), text, image_url, file_url, file_id, as_document, file_name, thumbnail_url):
                    sent += 1
            except Exception as e:
                logger.error(f"Failed to send to group {group.chat_id}: {e}")

    if to_channel and CHANNEL_ID:
        try:
            chat_id = str(CHANNEL_ID)
            if as_document:
                if file_url:
                    if await _send_file(chat_id, file_url, text, original_filename=file_name):
                        sent += 1
                if image_url:
                    if await _send_file(chat_id, image_url, text, original_filename=file_name):
                        sent += 1
            elif image_url:
                try:
                    msg = await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text)
                    sent += 1
                    channel_message_id = msg.message_id
                except Exception as e:
                    logger.warning(f"send_photo failed for channel {CHANNEL_ID}: {e}")
            elif file_url:
                if await _send_file(chat_id, file_url, text, original_filename=file_name):
                    sent += 1
            else:
                msg = await bot.send_message(chat_id=chat_id, text=text)
                sent += 1
                channel_message_id = msg.message_id
        except Exception as e:
            logger.error(f"Failed to send to channel {CHANNEL_ID}: {e}")

    return sent, channel_message_id


async def _send_file(chat_id: str, url: str, caption: str, original_filename: str = None) -> bool:
    if os.path.exists(url):
        try:
            filename = original_filename or os.path.basename(url)
            with open(url, 'rb') as f:
                await bot.send_document(chat_id=chat_id, document=f, filename=filename, caption=caption)
            return True
        except Exception as e:
            logger.warning(f"send_document local file failed for {chat_id}: {e}")
            return False

    if not original_filename:
        try:
            await bot.send_document(chat_id=chat_id, document=url, caption=caption)
            return True
        except Exception as e:
            logger.warning(f"send_document URL failed for {chat_id}: {e}")

    file_bytes = await asyncio.to_thread(download_raw, url)
    if file_bytes is None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=30)
                if resp.status_code == 200:
                    file_bytes = resp.content
            except Exception as e2:
                logger.warning(f"httpx download failed for {chat_id}: {e2}")

    if file_bytes:
        try:
            filename = original_filename or url.split("/")[-1].split("?")[0] or "file"
            await bot.send_document(chat_id=chat_id, document=file_bytes, filename=filename, caption=caption)
            return True
        except Exception as e3:
            logger.warning(f"send_document bytes failed for {chat_id}: {e3}")

    return False


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None) -> bool:
    try:
        if as_document:
            if file_url:
                if await _send_file(chat_id, file_url, text, original_filename=file_name):
                    return True
            if image_url:
                if await _send_file(chat_id, image_url, text, original_filename=file_name):
                    return True

        if image_url and not as_document:
            try:
                await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text)
                return True
            except Exception as e:
                logger.warning(f"send_photo failed for {chat_id}: {e}")

        if file_url:
            if await _send_file(chat_id, file_url, text, original_filename=file_name):
                return True

        if image_url:
            if await _send_file(chat_id, image_url, text, original_filename=file_name):
                return True

        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        logger.error(f"All send methods failed for {chat_id}: {e}")
        return False


async def delete_from_channel(channel_message_id: int) -> bool:
    if not CHANNEL_ID:
        return False
    try:
        await bot.delete_message(chat_id=CHANNEL_ID, message_id=channel_message_id)
        return True
    except Exception as e:
        logger.error(f"Failed to delete message {channel_message_id} from channel {CHANNEL_ID}: {e}")
        return False


async def delete_news_from_channel(channel_message_id: int) -> bool:
    return await delete_from_channel(channel_message_id)
