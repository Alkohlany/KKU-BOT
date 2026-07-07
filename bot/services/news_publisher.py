import logging
from bot.services.database import get_all_groups
from bot.config import BOT_TOKEN, CHANNEL_ID
from bot.services.cloud_storage import download_raw
import asyncio
import httpx
import os

logger = logging.getLogger(__name__)

MIME_TYPES = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'mp4': 'video/mp4',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'txt': 'text/plain',
    'zip': 'application/zip',
}


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, file_id: str = None, publish_to_channel: bool = False, as_document: bool = False, file_name: str = None, thumbnail_url: str = None):
    groups = await get_all_groups()
    sent = 0

    for group in groups:
        if not group.is_active:
            continue
        try:
            if await _send_to_chat(str(group.chat_id), text, image_url, file_url, file_id, as_document, file_name, thumbnail_url):
                sent += 1
        except Exception as e:
            logger.error(f"Failed to send to group {group.chat_id}: {e}")

    if publish_to_channel and CHANNEL_ID:
        try:
            if await _send_to_chat(str(CHANNEL_ID), text, image_url, file_url, file_id, as_document, file_name, thumbnail_url):
                sent += 1
        except Exception as e:
            logger.error(f"Failed to send to channel {CHANNEL_ID}: {e}")

    return sent


async def _send_document(chat_id: str, file_path: str, caption: str, filename: str = None) -> bool:
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return False

    if not filename:
        filename = os.path.basename(file_path)

    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    content_type = MIME_TYPES.get(ext, 'application/octet-stream')

    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'document': (filename, f, content_type)}
            data = {'chat_id': chat_id, 'caption': caption}
            resp = await client.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument',
                data=data,
                files=files,
                timeout=120
            )
        result = resp.json()
        if result.get('ok'):
            return True
        else:
            logger.warning(f"Telegram sendDocument failed: {result.get('description', 'unknown')}")
            return False


async def _send_document_with_thumbnail(chat_id: str, file_path: str, caption: str, thumbnail_path: str, filename: str = None) -> bool:
    if not os.path.exists(file_path):
        return False

    if not filename:
        filename = os.path.basename(file_path)

    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    content_type = MIME_TYPES.get(ext, 'application/octet-stream')

    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as doc_f:
            if thumbnail_path and os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as thumb_f:
                    files = {
                        'document': (filename, doc_f, content_type),
                        'thumb': ('thumb.jpg', thumb_f, 'image/jpeg')
                    }
            else:
                files = {'document': (filename, doc_f, content_type)}

            data = {'chat_id': chat_id, 'caption': caption}
            resp = await client.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument',
                data=data,
                files=files,
                timeout=120
            )
        result = resp.json()
        if result.get('ok'):
            return True
        else:
            logger.warning(f"Telegram sendDocument failed: {result.get('description', 'unknown')}")
            return False


async def _send_photo(chat_id: str, photo_path: str, caption: str) -> bool:
    if not os.path.exists(photo_path):
        return False

    async with httpx.AsyncClient() as client:
        with open(photo_path, 'rb') as f:
            files = {'photo': ('photo.jpg', f, 'image/jpeg')}
            data = {'chat_id': chat_id, 'caption': caption}
            resp = await client.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
                data=data,
                files=files,
                timeout=60
            )
        result = resp.json()
        return result.get('ok', False)


async def _send_url(chat_id: str, url: str, caption: str, filename: str = None) -> bool:
    async with httpx.AsyncClient() as client:
        data = {'chat_id': chat_id, 'document': url, 'caption': caption}
        if filename:
            data['filename'] = filename
        resp = await client.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument',
            data=data,
            timeout=60
        )
        result = resp.json()
        return result.get('ok', False)


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None, file_id: str = None, as_document: bool = False, file_name: str = None, thumbnail_url: str = None) -> bool:
    try:
        if as_document:
            if file_url:
                if await _send_document_with_thumbnail(chat_id, file_url, text, thumbnail_url, file_name):
                    return True
            if image_url:
                if os.path.exists(image_url):
                    if await _send_document(chat_id, image_url, text, file_name):
                        return True
                elif await _send_url(chat_id, image_url, text, file_name):
                    return True

        if image_url and not as_document:
            if os.path.exists(image_url):
                if await _send_photo(chat_id, image_url, text):
                    return True
            else:
                async with httpx.AsyncClient() as client:
                    data = {'chat_id': chat_id, 'photo': image_url, 'caption': text}
                    resp = await client.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto', data=data, timeout=60)
                    if resp.json().get('ok'):
                        return True

        if file_url:
            if await _send_document_with_thumbnail(chat_id, file_url, text, thumbnail_url, file_name):
                return True
            if await _send_url(chat_id, file_url, text, file_name):
                return True

        if image_url:
            if os.path.exists(image_url):
                if await _send_document(chat_id, image_url, text, file_name):
                    return True
            elif await _send_url(chat_id, image_url, text, file_name):
                return True

        async with httpx.AsyncClient() as client:
            data = {'chat_id': chat_id, 'text': text}
            await client.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', data=data, timeout=30)
        return True
    except Exception as e:
        logger.error(f"All send methods failed for {chat_id}: {e}")
        return False
