from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.middleware.subscription import subscription_required
from bot.services.database import get_auto_responses
import logging

logger = logging.getLogger(__name__)


async def responses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    responses = await get_auto_responses()
    if not responses:
        await update.message.reply_text("لا توجد ردود مخصصة حالياً 📭")
        return

    text = "💬 الردود المخصصة:\n\n"
    for r in responses:
        text += f"🔑 {r.keyword}\n"
        text += f"   ↳ {r.response[:80]}{'...' if len(r.response) > 80 else ''}\n\n"

    text += "\n💡 يمكنك إدارة الردود من الداشبورد"
    await update.message.reply_text(text)


responses_handler = CommandHandler("responses", responses_command)
