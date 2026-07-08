from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.services.database import get_active_channel_groups, log_activity
import logging

logger = logging.getLogger(__name__)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    
    if not context.args:
        await update.message.reply_text("استخدم: /broadcast <الرسالة>\nلنشر رسالة في جميع القروبات")
        return
    
    message = " ".join(context.args)
    groups = await get_active_channel_groups()
    
    sent = 0
    failed = 0
    for group in groups:
        try:
            await context.bot.send_message(chat_id=group.chat_id, text=message)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send to {group.chat_id}: {e}")
            failed += 1
    
    await log_activity(
        action="broadcast",
        details=f"Sent to {sent} groups, failed {failed}",
        performed_by=user.id
    )
    
    await update.message.reply_text(f"✅ تم النشر في {sent} قروب\n❌ فشل في {failed} قروب")


broadcast_handler = CommandHandler("broadcast", broadcast_command)
