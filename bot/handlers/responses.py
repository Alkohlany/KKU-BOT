from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.middleware.subscription import subscription_required
from bot.services.database import get_auto_responses
from bot.services.news_publisher import wrap_links_in_blockquote
import logging

logger = logging.getLogger(__name__)


async def responses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    responses = await get_auto_responses()
    if not responses:
        await update.message.reply_text("لا توجد ردود مخصصة حالياً 📭", disable_web_page_preview=True)
        return

    text = "💬 الردود المخصصة:\n\n"
    for r in responses:
        text += f"🔑 {r.keyword}\n"
        text += f"   ↳ {r.response[:80]}{'...' if len(r.response) > 80 else ''}\n\n"

    text += "\n💡 يمكنك إدارة الردود من الداشبورد"
    text = wrap_links_in_blockquote(text)
    await update.message.reply_text(text, parse_mode='HTML', disable_web_page_preview=True)


responses_handler = CommandHandler("responses", responses_command)
