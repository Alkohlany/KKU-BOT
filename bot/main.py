import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict
import httpx
from bot.config import BOT_TOKEN, ADMIN_IDS
from bot.services.database import init_db
from bot.handlers.start import start_handler, feature_handler
from bot.handlers.help import help_handler
from bot.handlers.admin import admin_text, admin_reply
from bot.handlers.admin_commands import get_admin_handlers
from bot.handlers.news import news_handler
from bot.handlers.questions import questions_handler
from bot.handlers.study_plans import plans_handler, plans_text_handler
from bot.handlers.broadcast import broadcast_handler
from bot.handlers.responses import responses_handler
from bot.services.protection import protection_handler, protection_media_handler
from bot.services.responses import auto_response_handler
from bot.middleware.subscription import check_subscription_handler, global_subscription_handler
from bot.handlers.group_handler import group_chat_member_handler, group_new_members_handler, register_group_cmd
from bot.services.scheduler import check_scheduled_posts

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application):
    try:
        await init_db()
        application.bot_data['admin_ids'] = ADMIN_IDS.copy()
        application.job_queue.run_repeating(check_scheduled_posts, interval=60, first=10)

        async def self_ping(context):
            port = os.environ.get("PORT", "8000")
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"http://127.0.0.1:{port}/health", timeout=10)
            except Exception:
                pass

        application.job_queue.run_repeating(self_ping, interval=300, first=30)
        logger.info("Database initialized and scheduler started")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        raise


async def error_handler(update, context):
    if isinstance(context.error, Conflict):
        logger.warning("Conflict detected - another bot instance is active (likely deployment overlap). Waiting for it to disconnect...")
        return
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)


def main():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_error_handler(error_handler)

    application.add_handler(start_handler)
    application.add_handler(feature_handler)
    application.add_handler(help_handler)
    application.add_handler(news_handler)
    application.add_handler(questions_handler)
    application.add_handler(plans_handler)
    application.add_handler(plans_text_handler)
    application.add_handler(broadcast_handler)
    application.add_handler(responses_handler)
    application.add_handler(admin_text)
    application.add_handler(admin_reply)

    for handler in get_admin_handlers():
        application.add_handler(handler)

    application.add_handler(check_subscription_handler)
    application.add_handler(global_subscription_handler, group=-1)
    application.add_handler(group_chat_member_handler)
    application.add_handler(group_new_members_handler)
    application.add_handler(register_group_cmd)
    application.add_handler(protection_handler, group=1)
    application.add_handler(protection_media_handler, group=1)
    application.add_handler(auto_response_handler, group=2)

    logger.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
