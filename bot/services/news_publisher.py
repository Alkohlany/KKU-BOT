import httpx
import os
import mimetypes
import asyncio
import logging
from bot.services.database import get_all_groups
from bot.config import BOT_TOKEN, CHANNEL_ID
from bot.services.cloud_storage import download_raw

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, publish_to_channel: bool = False, as_document: bool = False):
    groups = await get_all_groups()
    sent = 0

    for group in groups:
        if not group.is_active:
            continue
        try:
            if await _send_to_chat(str(group.chat_id), text, image_url, file_url, as_document):
                sent += 1
        except Exception as e:
            logger.error(f"Failed to send to group {group.chat_id}: {e}")

    if publish_to_channel and CHANNEL_ID:
        try:
            if await _send_to_chat(str(CHANNEL_ID), text, image_url, file_url, as_document):
                sent += 1
        except Exception as e:
            logger.error(f"Failed to send to channel {CHANNEL_ID}: {e}")

    return sent


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None, as_document: bool = False) -> bool:
    async with httpx.AsyncClient() as client:
        sent_ok = False
        
        if as_document and (image_url or file_url):
            url = image_url or file_url
            filepath = _resolve_file(url)
            if filepath and os.path.exists(filepath):
                content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
                try:
                    with open(filepath, "rb") as f:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                            data={"chat_id": chat_id, "caption": text},
                            files={"document": (os.path.basename(filepath), f, content_type)},
                            timeout=30
                        )
                        sent_ok = resp.status_code == 200
                except Exception as e:
                    logger.error(f"Error sending document to {chat_id}: {e}")
            elif url.startswith("http"):
                try:
                    file_bytes = await asyncio.to_thread(download_raw, url)
                    if file_bytes is None:
                        file_resp = await client.get(url, timeout=30)
                        if file_resp.status_code != 200:
                            logger.error(f"Failed to download file from {url}: {file_resp.status_code}")
                        else:
                            file_bytes = file_resp.content
                    if file_bytes:
                        filename = url.split("/")[-1].split("?")[0] or "document"
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                            data={"chat_id": chat_id, "caption": text},
                            files={"document": (filename, file_bytes, "application/octet-stream")},
                            timeout=30
                        )
                        if resp.status_code != 200:
                            logger.error(f"sendDocument failed for {chat_id}: {resp.text}")
                        sent_ok = resp.status_code == 200
                    if not sent_ok:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": text},
                            timeout=30
                        )
                        if resp.status_code != 200:
                            logger.error(f"sendMessage fallback failed for {chat_id}: {resp.text}")
                        sent_ok = resp.status_code == 200
                except Exception as e:
                    logger.error(f"Error sending document to {chat_id}: {e}")
                    try:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": text},
                            timeout=30
                        )
                        sent_ok = resp.status_code == 200
                    except Exception as e2:
                        logger.error(f"Error sending text fallback to {chat_id}: {e2}")
            return sent_ok
        
        if image_url:
            filepath = _resolve_file(image_url)
            if filepath and os.path.exists(filepath):
                content_type = mimetypes.guess_type(filepath)[0] or "image/jpeg"
                try:
                    with open(filepath, "rb") as f:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                            data={"chat_id": chat_id, "caption": text},
                            files={"photo": (os.path.basename(filepath), f, content_type)},
                            timeout=30
                        )
                        sent_ok = resp.status_code == 200
                        if not sent_ok:
                            logger.error(f"sendPhoto failed for {chat_id}: {resp.text}")
                except Exception as e:
                    logger.error(f"Error sending photo to {chat_id}: {e}")
            elif image_url.startswith("http"):
                try:
                    file_resp = await client.get(image_url, timeout=30)
                    if file_resp.status_code != 200:
                        logger.error(f"Failed to download image from {image_url}: {file_resp.status_code}")
                    else:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                            data={"chat_id": chat_id, "caption": text},
                            files={"photo": ("image", file_resp.content, file_resp.headers.get("content-type", "image/jpeg"))},
                            timeout=30
                        )
                        if resp.status_code != 200:
                            logger.error(f"sendPhoto failed for {chat_id}: {resp.text}")
                        sent_ok = resp.status_code == 200
                except Exception as e:
                    logger.error(f"Error sending photo to {chat_id}: {e}")

        if file_url and not sent_ok:
            filepath = _resolve_file(file_url)
            if filepath and os.path.exists(filepath):
                content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
                try:
                    with open(filepath, "rb") as f:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                            data={"chat_id": chat_id, "caption": text},
                            files={"document": (os.path.basename(filepath), f, content_type)},
                            timeout=30
                        )
                        if resp.status_code != 200:
                            logger.error(f"sendDocument failed for {chat_id}: {resp.text}")
                        sent_ok = resp.status_code == 200
                except Exception as e:
                    logger.error(f"Error sending document to {chat_id}: {e}")
            elif file_url.startswith("http"):
                try:
                    file_bytes = await asyncio.to_thread(download_raw, url=file_url)
                    if file_bytes is None:
                        file_resp = await client.get(file_url, timeout=30)
                        if file_resp.status_code != 200:
                            logger.error(f"Failed to download file from {file_url}: {file_resp.status_code}")
                        else:
                            file_bytes = file_resp.content
                    if file_bytes:
                        filename = file_url.split("/")[-1].split("?")[0] or "document"
                        resp = await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                            data={"chat_id": chat_id, "caption": text},
                            files={"document": (filename, file_bytes, "application/octet-stream")},
                            timeout=30
                        )
                        if resp.status_code != 200:
                            logger.error(f"sendDocument failed for {chat_id}: {resp.text}")
                        sent_ok = resp.status_code == 200
                except Exception as e:
                    logger.error(f"Error sending document to {chat_id}: {e}")

        if not sent_ok:
            try:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                    timeout=30
                )
                if resp.status_code != 200:
                    logger.error(f"sendMessage failed for {chat_id}: {resp.text}")
                sent_ok = resp.status_code == 200
            except Exception as e:
                logger.error(f"Error sending message to {chat_id}: {e}")
        
        return sent_ok


def _resolve_file(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("/"):
        filename = os.path.basename(url)
        return os.path.join(UPLOAD_DIR, filename)
    return None
