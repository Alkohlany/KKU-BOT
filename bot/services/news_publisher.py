import logging
import re
import json
from telegram import Bot, InputMediaPhoto, InputMediaDocument, InputMediaVideo
from bot.services.database import get_active_channel_groups, log_activity
from bot.config import BOT_TOKEN
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


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None, target_channels: str = None, files_json: str = None) -> tuple[int, int | None, dict]:
    text = wrap_links_in_blockquote(text)
    sent = 0
    channel_message_id = None
    group_message_ids = {}

    if not target_channels:
        logger.warning("No target_channels specified, skipping publish")
        return sent, channel_message_id, group_message_ids

    try:
        target_chat_ids = json.loads(target_channels)
    except (json.JSONDecodeError, TypeError):
        logger.error(f"Invalid target_channels JSON: {target_channels}")
        return sent, channel_message_id, group_message_ids

    logger.info(f"target_chat_ids: {target_chat_ids}")

    for chat_id in target_chat_ids:
        chat_id_str = str(chat_id)
        try:
            msg_id = await _send_to_chat_and_get_id(chat_id_str, text, image_url, file_url, file_id, as_document, file_name, thumbnail_url, files_json=files_json)
            if msg_id:
                sent += 1
                if isinstance(msg_id, list):
                    group_message_ids[chat_id_str] = msg_id
                else:
                    group_message_ids[chat_id_str] = msg_id
        except Exception as e:
            logger.error(f"Failed to send to {chat_id_str}: {e}")

    if sent > 0:
        try:
            await log_activity(
                action="news_published",
                details=f"نشر خبر: {text[:50]}...",
                performed_by=0
            )
        except Exception as e:
            logger.warning(f"Failed to log publish activity: {e}")

    return sent, channel_message_id, group_message_ids


async def _send_file(chat_id: str, url: str, caption: str, original_filename: str = None, thumb_url: str = None) -> bool:
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


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None, files_json: str = None) -> bool:
    msg_id = await _send_to_chat_and_get_id(chat_id, text, image_url, file_url, file_id, as_document, file_name, thumbnail_url, files_json=files_json)
    return msg_id is not None


async def _send_to_chat_and_get_id(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None, files_json: str = None) -> int | list | None:
    logger.info(f"Sending to {chat_id}, as_document={as_document}, file_url={file_url}, image_url={image_url}")

    if files_json:
        try:
            parsed_files = json.loads(files_json)
        except (json.JSONDecodeError, TypeError):
            parsed_files = []

        if parsed_files:
            if len(parsed_files) > 1:
                return await _send_media_group(chat_id, text, parsed_files, as_document)
            else:
                file_obj = parsed_files[0]
                file_url_item = file_obj.get("url")
                file_type_item = file_obj.get("type", "document")
                file_name_item = file_obj.get("name")
                file_thumb_item = file_obj.get("thumbnail")
                try:
                    if file_type_item == "photo" and not as_document:
                        msg = await bot.send_photo(chat_id=chat_id, photo=file_url_item, caption=text, parse_mode='HTML')
                        return msg.message_id
                    else:
                        msg = await _send_file_and_get_id(chat_id, file_url_item, text, original_filename=file_name_item, thumb_url=file_thumb_item)
                        if msg:
                            return msg.message_id
                except Exception as e:
                    logger.warning(f"Failed to send file {file_name_item} to {chat_id}: {e}")

    try:
        if as_document:
            if file_url:
                msg = await _send_file_and_get_id(chat_id, file_url, text, original_filename=file_name, thumb_url=thumbnail_url)
                if msg:
                    return msg.message_id
            if image_url:
                msg = await _send_file_and_get_id(chat_id, image_url, text, original_filename=file_name, thumb_url=thumbnail_url)
                if msg:
                    return msg.message_id

        if image_url and not as_document:
            try:
                msg = await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text, parse_mode='HTML')
                return msg.message_id
            except Exception as e:
                logger.warning(f"send_photo failed for {chat_id}: {e}")

        if file_url:
            msg = await _send_file_and_get_id(chat_id, file_url, text, original_filename=file_name, thumb_url=thumbnail_url)
            if msg:
                return msg.message_id

        if image_url:
            msg = await _send_file_and_get_id(chat_id, image_url, text, original_filename=file_name, thumb_url=thumbnail_url)
            if msg:
                return msg.message_id

        msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', disable_web_page_preview=True)
        return msg.message_id
    except Exception as e:
        logger.error(f"All send methods failed for {chat_id}: {e}")
        return None


async def _send_file_and_get_id(chat_id: str, url: str, caption: str, original_filename: str = None, thumb_url: str = None):
    if url.startswith('http'):
        try:
            filename = original_filename or url.split("/")[-1].split("?")[0] or "file"
            async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    from io import BytesIO
                    bio = BytesIO(resp.content)
                    bio.name = filename
                    kwargs = dict(chat_id=chat_id, document=bio, filename=filename, caption=caption, parse_mode='HTML')
                    if thumb_url and thumb_url.startswith('http'):
                        try:
                            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as tclient:
                                tresp = await tclient.get(thumb_url)
                                if tresp.status_code == 200:
                                    kwargs['thumbnail'] = tresp.content
                        except:
                            pass
                    return await bot.send_document(**kwargs)
        except Exception as e:
            logger.warning(f"send_document failed for {chat_id}: {e}")

    if os.path.exists(url):
        try:
            filename = original_filename or os.path.basename(url)
            with open(url, 'rb') as f:
                kwargs = dict(chat_id=chat_id, document=f, filename=filename, caption=caption, parse_mode='HTML')
                if thumb_url and thumb_url.startswith('http'):
                    try:
                        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as tclient:
                            tresp = await tclient.get(thumb_url)
                            if tresp.status_code == 200:
                                kwargs['thumbnail'] = tresp.content
                    except:
                        pass
                return await bot.send_document(**kwargs)
        except Exception as e:
            logger.warning(f"send_document local file failed for {chat_id}: {e}")

    return None


async def _send_media_group(chat_id: str, caption: str, parsed_files: list, as_document: bool = False) -> list | None:
    media_group = []
    for i, file_obj in enumerate(parsed_files):
        file_url_item = file_obj.get("url")
        file_type_item = file_obj.get("type", "document")
        item_caption = caption if i == len(parsed_files) - 1 else None

        if os.path.exists(file_url_item):
            media = open(file_url_item, 'rb')
        else:
            media = file_url_item

        if file_type_item == "photo" and not as_document:
            media_group.append(InputMediaPhoto(media=media, caption=item_caption, parse_mode='HTML'))
        elif file_type_item == "video":
            media_group.append(InputMediaVideo(media=media, caption=item_caption, parse_mode='HTML'))
        else:
            file_name_item = file_obj.get("name")
            item_thumb = file_obj.get("thumbnail")
            item_thumb_data = None
            if item_thumb and item_thumb.startswith('http'):
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                        resp = await client.get(item_thumb)
                        if resp.status_code == 200:
                            item_thumb_data = resp.content
                except:
                    pass
            doc_kwargs = dict(media=media, caption=item_caption, parse_mode='HTML', filename=file_name_item)
            if item_thumb_data:
                doc_kwargs['thumbnail'] = item_thumb_data
            media_group.append(InputMediaDocument(**doc_kwargs))

    if not media_group:
        return None

    try:
        messages = await bot.send_media_group(chat_id=chat_id, media=media_group)

        if messages:
            return [msg.message_id for msg in messages]
    except Exception as e:
        logger.warning(f"send_media_group failed for {chat_id}: {e}")
    finally:
        for item in media_group:
            if hasattr(item.media, 'close'):
                item.media.close()

    return None


async def delete_from_channel(channel_message_id) -> bool:
    channel = None
    groups = await get_active_channel_groups()
    for ch in groups:
        if ch.type == 'channel':
            channel = ch
            break
    if not channel:
        return False
    ids_to_delete = channel_message_id if isinstance(channel_message_id, list) else [channel_message_id]
    deleted = 0
    for msg_id in ids_to_delete:
        try:
            await bot.delete_message(chat_id=channel.chat_id, message_id=msg_id)
            deleted += 1
        except Exception as e:
            logger.error(f"Failed to delete message {msg_id} from channel {channel.chat_id}: {e}")
    return deleted > 0


async def delete_news_from_channel(channel_message_id: int) -> bool:
    return await delete_from_channel(channel_message_id)


async def delete_from_groups(group_message_ids) -> bool:
    if not group_message_ids:
        return False
    if isinstance(group_message_ids, str):
        try:
            group_message_ids = json.loads(group_message_ids)
        except:
            return False
    deleted = 0
    for chat_id_str, msg_ids in group_message_ids.items():
        ids_to_delete = msg_ids if isinstance(msg_ids, list) else [msg_ids]
        for message_id in ids_to_delete:
            try:
                await bot.delete_message(chat_id=chat_id_str, message_id=message_id)
                deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete message {message_id} from group {chat_id_str}: {e}")
    return deleted > 0


async def edit_published_message(chat_id: str, message_id: int, text: str, image_url: str = None, file_url: str = None, as_document: bool = False, file_name: str = None) -> bool:
    """Edit an already published message in a group or channel"""
    has_media = image_url or file_url
    # Try edit_message_caption for messages with media (photos, videos, documents)
    if has_media:
        try:
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, parse_mode='HTML')
            return True
        except Exception as e:
            logger.warning(f"edit_message_caption failed for {chat_id} msg {message_id}: {e}")
    # Try edit_message_text for text-only messages
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode='HTML')
        return True
    except Exception as e:
        logger.warning(f"edit_message_text failed for {chat_id} msg {message_id}: {e}")
        return False


async def edit_published_messages(text: str, group_message_ids: dict, channel_message_id: int = None, image_url: str = None, file_url: str = None, as_document: bool = False, file_name: str = None) -> tuple[int, int]:
    """Edit all published messages in groups and channel"""
    text = wrap_links_in_blockquote(text)
    edited = 0
    failed = 0

    # Edit group messages
    if group_message_ids:
        for chat_id_str, msg_ids in group_message_ids.items():
            ids_to_edit = msg_ids if isinstance(msg_ids, list) else [msg_ids]
            # For media groups, only edit the last message (has the caption)
            last_id = ids_to_edit[-1]
            try:
                if await edit_published_message(chat_id_str, last_id, text, image_url, file_url, as_document, file_name):
                    edited += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to edit message {last_id} in {chat_id_str}: {e}")
                failed += 1

    # Edit channel message
    if channel_message_id:
        channel = None
        groups = await get_active_channel_groups()
        for ch in groups:
            if ch.type == 'channel':
                channel = ch
                break
        if channel:
            try:
                if await edit_published_message(str(channel.chat_id), channel_message_id, text, image_url, file_url, as_document, file_name):
                    edited += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to edit channel message: {e}")
                failed += 1

    return edited, failed


async def resend_published_messages(text: str, group_message_ids: dict, channel_message_id: int = None, image_url: str = None, file_url: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None, files_json: str = None) -> tuple[int, int, dict, int]:
    """Delete old messages and resend with updated content/files. Returns (sent, failed, new_group_message_ids, new_channel_message_id)"""
    text = wrap_links_in_blockquote(text)
    sent = 0
    failed = 0
    new_group_message_ids = {}
    new_channel_message_id = None

    if group_message_ids:
        for chat_id_str, msg_ids in group_message_ids.items():
            ids_to_delete = msg_ids if isinstance(msg_ids, list) else [msg_ids]
            for mid in ids_to_delete:
                try:
                    await bot.delete_message(chat_id=chat_id_str, message_id=mid)
                except Exception as e:
                    logger.warning(f"Failed to delete message {mid} in {chat_id_str}: {e}")
            try:
                new_msg_id = await _send_to_chat_and_get_id(chat_id_str, text, image_url, file_url, None, as_document, file_name, thumbnail_url, files_json=files_json)
                if new_msg_id:
                    sent += 1
                    new_group_message_ids[chat_id_str] = new_msg_id
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to resend to {chat_id_str}: {e}")
                failed += 1

    if channel_message_id:
        channel = None
        groups = await get_active_channel_groups()
        for ch in groups:
            if ch.type == 'channel':
                channel = ch
                break
        if channel:
            try:
                await bot.delete_message(chat_id=str(channel.chat_id), message_id=channel_message_id)
            except Exception as e:
                logger.warning(f"Failed to delete channel message {channel_message_id}: {e}")
            try:
                new_msg_id = await _send_to_chat_and_get_id(str(channel.chat_id), text, image_url, file_url, None, as_document, file_name, thumbnail_url, files_json=files_json)
                if new_msg_id:
                    sent += 1
                    new_channel_message_id = new_msg_id
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to resend to channel: {e}")
                failed += 1

    return sent, failed, new_group_message_ids, new_channel_message_id
