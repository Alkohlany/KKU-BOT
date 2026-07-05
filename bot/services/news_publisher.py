import httpx
import os
import mimetypes
import logging
from bot.services.database import get_all_groups
from bot.config import BOT_TOKEN

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None):
    groups = await get_all_groups()
    sent = 0

    for group in groups:
        if not group.is_active:
            continue
        try:
            await _send_to_chat(str(group.chat_id), text, image_url, file_url)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send to group {group.chat_id}: {e}")

    return sent


async def _send_to_chat(chat_id: str, text: str, image_url: str = None, file_url: str = None):
    async with httpx.AsyncClient() as client:
        sent_photo = False
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
                        sent_photo = resp.status_code == 200
                        if not sent_photo:
                            logger.error(f"sendPhoto failed for {chat_id}: {resp.text}")
                except Exception as e:
                    logger.error(f"Error sending photo to {chat_id}: {e}")
            elif image_url.startswith("http"):
                try:
                    resp = await client.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                        json={"chat_id": chat_id, "photo": image_url, "caption": text},
                        timeout=30
                    )
                    sent_photo = resp.status_code == 200
                except Exception as e:
                    logger.error(f"Error sending photo URL to {chat_id}: {e}")

        if file_url and not sent_photo:
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
                except Exception as e:
                    logger.error(f"Error sending document to {chat_id}: {e}")
            elif file_url.startswith("http"):
                try:
                    resp = await client.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                        json={"chat_id": chat_id, "document": file_url, "caption": text},
                        timeout=30
                    )
                except Exception as e:
                    logger.error(f"Error sending document URL to {chat_id}: {e}")

        if not sent_photo and not file_url:
            try:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                    timeout=30
                )
                if resp.status_code != 200:
                    logger.error(f"sendMessage failed for {chat_id}: {resp.text}")
            except Exception as e:
                logger.error(f"Error sending message to {chat_id}: {e}")


def _resolve_file(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("/"):
        filename = os.path.basename(url)
        return os.path.join(UPLOAD_DIR, filename)
    return None
