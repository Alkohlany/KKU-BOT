import logging
import re
import json
from telegram import Bot
from bot.services.database import get_active_channel_groups
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


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, file_id: str = None, to_groups: bool = True, to_channel: bool = False, as_document: bool = False, file_name: str = None, thumbnail_url: str = None, target_channels: str = None) -> tuple[int, int | None, dict]:
    text = wrap_links_in_blockquote(text)
    groups = await get_active_channel_groups()
    sent = 0
    channel_message_id = None
    group_message_ids = {}

    target_chat_ids = None
    if target_channels:
        try:
            target_chat_ids = json.loads(target_channels)
        except (json.JSONDecodeError, TypeError):
            target_chat_ids = None

    if to_groups:
        for group in groups:
            if not group.is_active:
                continue
            if target_chat_ids is not None and str(group.chat_id) not in [str(cid) for cid in target_chat_ids]:
                continue
            try:
                msg_id = await _send_to_chat_and_get_id(str(group.chat_id), text, image_url, file_url, file_id, as_document, file_name, thumbnail_url)
                if msg_id:
                    sent += 1
                    group_message_ids[str(group.chat_id)] = msg_id
            except Exception as e:
                logger.error(f"Failed to send to group {group.chat_id}: {e}")

    if to_channel and CHANNEL_ID:
        if target_chat_ids is None or str(CHANNEL_ID) in [str(cid) for cid in target_chat_ids]:
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

    return sent, channel_message_id, group_message_ids


async def _send_file(chat_id: str, url: str, caption: str, original_filename: str = None) -> bool:
    if os.path.exists(url):
        try:
            filename = original_filename or os.path.basename(url)
            with open(url, 'rb') as f:
                await bot.send_document(chat_id=chat_id, document=f, filename=filename, caption=caption, parse_mode='HTML')
            return True
        except Exception as e:
            logger.warning(f"send_document local file failed for {chat_id}: {e}")
            return False

    if not original_filename:
        try:
            await bot.send_document(chat_id=chat_id, document=url, caption=caption, parse_mode='HTML')
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
            await bot.send_document(chat_id=chat_id, document=file_bytes, filename=filename, caption=caption, parse_mode='HTML')
            return True
        except Exception as e3:
            logger.warning(f"send_document bytes failed for {chat_id}: {e3}")

    return False


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None) -> bool:
    msg_id = await _send_to_chat_and_get_id(chat_id, text, image_url, file_url, file_id, as_document, file_name, thumbnail_url)
    return msg_id is not None


async def _send_to_chat_and_get_id(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None) -> int | None:
    try:
        if as_document:
            if file_url:
                msg = await _send_file_and_get_id(chat_id, file_url, text, original_filename=file_name)
                if msg:
                    return msg.message_id
            if image_url:
                msg = await _send_file_and_get_id(chat_id, image_url, text, original_filename=file_name)
                if msg:
                    return msg.message_id

        if image_url and not as_document:
            try:
                msg = await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text, parse_mode='HTML')
                return msg.message_id
            except Exception as e:
                logger.warning(f"send_photo failed for {chat_id}: {e}")

        if file_url:
            msg = await _send_file_and_get_id(chat_id, file_url, text, original_filename=file_name)
            if msg:
                return msg.message_id

        if image_url:
            msg = await _send_file_and_get_id(chat_id, image_url, text, original_filename=file_name)
            if msg:
                return msg.message_id

        msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        return msg.message_id
    except Exception as e:
        logger.error(f"All send methods failed for {chat_id}: {e}")
        return None


async def _send_file_and_get_id(chat_id: str, url: str, caption: str, original_filename: str = None):
    if os.path.exists(url):
        try:
            filename = original_filename or os.path.basename(url)
            with open(url, 'rb') as f:
                return await bot.send_document(chat_id=chat_id, document=f, filename=filename, caption=caption, parse_mode='HTML')
        except Exception as e:
            logger.warning(f"send_document local file failed for {chat_id}: {e}")
            return None

    if not original_filename:
        try:
            return await bot.send_document(chat_id=chat_id, document=url, caption=caption, parse_mode='HTML')
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
            return await bot.send_document(chat_id=chat_id, document=file_bytes, filename=filename, caption=caption, parse_mode='HTML')
        except Exception as e3:
            logger.warning(f"send_document bytes failed for {chat_id}: {e3}")

    return None


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


async def edit_published_message(chat_id: str, message_id: int, text: str, image_url: str = None, file_url: str = None, as_document: bool = False, file_name: str = None) -> bool:
    """Edit an already published message in a group or channel"""
    try:
        if as_document:
            if file_url:
                try:
                    await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, parse_mode='HTML')
                    return True
                except Exception as e:
                    logger.warning(f"edit_message_caption failed for {chat_id}: {e}")
            if image_url:
                try:
                    await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, parse_mode='HTML')
                    return True
                except Exception as e:
                    logger.warning(f"edit_message_caption failed for {chat_id}: {e}")
        
        if image_url and not as_document:
            try:
                await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, parse_mode='HTML')
                return True
            except Exception as e:
                logger.warning(f"edit_message_caption failed for {chat_id}: {e}")

        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode='HTML')
            return True
        except Exception as e:
            logger.warning(f"edit_message_text failed for {chat_id}: {e}")
            return False
    except Exception as e:
        logger.error(f"Failed to edit message {message_id} in {chat_id}: {e}")
        return False


async def edit_published_messages(text: str, group_message_ids: dict, channel_message_id: int = None, image_url: str = None, file_url: str = None, as_document: bool = False, file_name: str = None) -> tuple[int, int]:
    """Edit all published messages in groups and channel"""
    text = wrap_links_in_blockquote(text)
    edited = 0
    failed = 0
    
    # Edit group messages
    if group_message_ids:
        for chat_id_str, message_id in group_message_ids.items():
            try:
                if await edit_published_message(chat_id_str, message_id, text, image_url, file_url, as_document, file_name):
                    edited += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to edit message in {chat_id_str}: {e}")
                failed += 1
    
    # Edit channel message
    if channel_message_id and CHANNEL_ID:
        try:
            if await edit_published_message(str(CHANNEL_ID), channel_message_id, text, image_url, file_url, as_document, file_name):
                edited += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to edit channel message: {e}")
            failed += 1
    
    return edited, failed
