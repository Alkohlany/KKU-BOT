import logging
from telegram import Bot
from bot.services.database import get_all_groups
from bot.config import BOT_TOKEN, CHANNEL_ID

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)


async def publish_to_groups(text: str, image_url: str = None, file_url: str = None, file_name: str = None, publish_to_channel: bool = False, as_document: bool = False):
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
    try:
        if as_document:
            url = image_url or file_url
            if url:
                try:
                    await bot.send_document(chat_id=chat_id, document=url, caption=text)
                    return True
                except Exception as e:
                    logger.warning(f"send_document failed for {chat_id}: {e}")

        if image_url and not as_document:
            try:
                await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text)
                return True
            except Exception as e:
                logger.warning(f"send_photo failed for {chat_id}: {e}")

        if file_url:
            try:
                await bot.send_document(chat_id=chat_id, document=file_url, caption=text)
                return True
            except Exception as e:
                logger.warning(f"send_document failed for {chat_id}: {e}")

        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        logger.error(f"All send methods failed for {chat_id}: {e}")
        return False
