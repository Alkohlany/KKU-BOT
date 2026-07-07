import logging
from telegram import Bot
from bot.services.database import get_all_groups
from bot.config import BOT_TOKEN, CHANNEL_ID
from bot.services.cloud_storage import download_raw
import asyncio
import httpx

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, file_id: str = None, publish_to_channel: bool = False, as_document: bool = False, file_name: str = None):
    groups = await get_all_groups()
    sent = 0

    for group in groups:
        if not group.is_active:
            continue
        try:
            if await _send_to_chat(str(group.chat_id), text, image_url, file_url, file_id, as_document, file_name):
                sent += 1
        except Exception as e:
            logger.error(f"Failed to send to group {group.chat_id}: {e}")

    if publish_to_channel and CHANNEL_ID:
        try:
            if await _send_to_chat(str(CHANNEL_ID), text, image_url, file_url, file_id, as_document, file_name):
                sent += 1
        except Exception as e:
            logger.error(f"Failed to send to channel {CHANNEL_ID}: {e}")

    return sent


async def _send_file(chat_id: str, url: str, caption: str, original_filename: str = None) -> bool:
    """Try sending URL directly first, then download-and-upload as fallback."""
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


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None) -> bool:
    try:
        if as_document:
            if file_id:
                await bot.send_document(chat_id=chat_id, document=file_id, caption=text)
                return True
            url = image_url or file_url
            if url:
                if await _send_file(chat_id, url, text, original_filename=file_name):
                    return True

        if image_url and not as_document:
            try:
                await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text)
                return True
            except Exception as e:
                logger.warning(f"send_photo failed for {chat_id}: {e}")

        if file_id:
            await bot.send_document(chat_id=chat_id, document=file_id, caption=text)
            return True

        if file_url:
            if await _send_file(chat_id, file_url, text, original_filename=file_name):
                return True

        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        logger.error(f"All send methods failed for {chat_id}: {e}")
        return False
