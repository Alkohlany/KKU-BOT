from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from bot.middleware.subscription import subscription_required
from bot.services.database import get_user, create_user
from bot.handlers.student_menu import MAIN_MENU_TEXT, build_main_menu
import logging

logger = logging.getLogger(__name__)

START_MESSAGE = MAIN_MENU_TEXT


FEATURES_KEYBOARD = [
    [InlineKeyboardButton("📰 المنشورات", callback_data="feature_news")],
    [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="feature_questions")],
    [InlineKeyboardButton("📋 الخطط الدراسية", callback_data="feature_plans")],
    [InlineKeyboardButton("💬 الردود", callback_data="feature_responses")],
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    if context.args and context.args[0] == "plans":
        from bot.handlers.study_plans import plans_command
        await plans_command(update, context)
        return

    await update.message.reply_text(
        START_MESSAGE,
        parse_mode="HTML",
        reply_markup=build_main_menu(),
        disable_web_page_preview=True,
    )


async def feature_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    feature = query.data.replace("feature_", "")
    
    if feature == "news":
        from bot.handlers.news import get_news_text
        text = await get_news_text()
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    elif feature in {"questions", "responses"}:
        # دعم الأزرار القديمة الموجودة في رسائل سابقة دون استدعاء وظائف أزيلت.
        await query.edit_message_text(
            MAIN_MENU_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_main_menu(),
        )
    elif feature == "plans":
        from bot.handlers.study_plans import get_plans_text
        text = await get_plans_text()
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)


start_handler = CommandHandler("start", start_command)
feature_handler = CallbackQueryHandler(feature_callback, pattern="^feature_")
