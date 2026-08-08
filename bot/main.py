import logging
import sys
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import Conflict
from bot.config import BOT_TOKEN, ADMIN_IDS
from bot.handlers.start import start_handler, feature_handler
from bot.handlers.help import help_handler
from bot.handlers.admin import admin_text, admin_reply
from bot.handlers.admin_commands import (
    admin_command, response_handler, question_handler, news_handler as admin_news_handler,
    stats_command, groups_command, broadcast_command,
    ban_command, unban_command, banned_list, spam_handler
)
from bot.handlers.admin_menu import admin_panel_command, admin_panel_text, admin_panel_callback
from bot.handlers.news import news_handler
from bot.handlers.questions import questions_handler
from bot.handlers.study_plans import plans_handler, plans_text_handler
from bot.handlers.books import books_handler, books_text_handler
from bot.handlers.broadcast import broadcast_handler
from bot.handlers.responses import responses_handler
from bot.handlers.student_menu import menu_handler, menu_text_handler, menu_callback_handler
from bot.services.protection import protection_handler, protection_media_handler
from bot.services.responses import auto_response_handler
from bot.middleware.subscription import check_subscription_handler, global_subscription_handler
from bot.handlers.group_handler import group_chat_member_handler, group_new_members_handler, register_group_cmd
from bot.handlers.channel_handler import channel_chat_member_handler, register_channel_cmd
from bot.services.scheduler import check_scheduled_posts
from bot.services.database import init_db, run_migrations, add_missing_columns
from bot.handlers import student_menu

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def post_init(application):
    try:
        application.bot_data['admin_ids'] = ADMIN_IDS.copy()
        try:
            me = await application.bot.get_me()
            student_menu._bot_username = me.username
        except Exception as bot_error:
            logger.warning(f"Could not fetch bot username: {bot_error}")
        try:
            await application.bot.set_my_commands([
                BotCommand('start', 'بدء استخدام البوت'),
                BotCommand('menu', 'فتح القائمة الرئيسية'),
                BotCommand('plans', 'الخطط الدراسية'),
                BotCommand('books', 'الكتب'),
                BotCommand('news', 'المنشورات'),
                BotCommand('help', 'المساعدة'),
            ])
        except Exception as command_error:
            logger.warning(f"Could not update Telegram bot commands: {command_error}")
        application.job_queue.run_repeating(check_scheduled_posts, interval=60, first=10)
        logger.info("Scheduler started")
    except Exception as e:
        logger.critical(f"Failed to initialize: {e}", exc_info=True)
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
    application.add_handler(menu_handler)
    application.add_handler(menu_text_handler)
    application.add_handler(menu_callback_handler)
    application.add_handler(feature_handler)
    application.add_handler(help_handler)
    application.add_handler(news_handler)
    application.add_handler(questions_handler)
    application.add_handler(plans_handler)
    application.add_handler(plans_text_handler)
    application.add_handler(books_handler)
    application.add_handler(books_text_handler)
    application.add_handler(broadcast_handler)
    application.add_handler(responses_handler)
    application.add_handler(admin_text)
    application.add_handler(admin_reply)

    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("r", response_handler))
    application.add_handler(CommandHandler("q", question_handler))
    application.add_handler(CommandHandler("n", admin_news_handler))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("groups", groups_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("banned", banned_list))
    application.add_handler(CommandHandler("spam", spam_handler))

    application.add_handler(admin_panel_command)
    application.add_handler(admin_panel_callback)
    application.add_handler(admin_panel_text)

    application.add_handler(check_subscription_handler)
    application.add_handler(global_subscription_handler, group=-1)
    application.add_handler(group_chat_member_handler)
    application.add_handler(channel_chat_member_handler)
    application.add_handler(register_channel_cmd)
    application.add_handler(group_new_members_handler)
    application.add_handler(register_group_cmd)
    application.add_handler(protection_handler, group=1)
    application.add_handler(protection_media_handler, group=1)
    application.add_handler(auto_response_handler, group=2)

    logger.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
