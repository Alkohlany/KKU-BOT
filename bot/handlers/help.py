from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.middleware.subscription import subscription_required
from bot.config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

HELP_MESSAGE = """📚 أوامر البوت

👤 أوامر عامة:
/start - بدء استخدام البوت
/help - عرض هذه الرسالة

📋 أوامر القروب (للمشرفين):
/add_response - إضافة رد تلقائي
/del_response - حذف رد تلقائي
/list_responses - عرض جميع الردود

🛡️ أوامر الحماية:
/ban - حظر مستخدم
/unban - إلغاء حظر مستخدم
/banned_list - قائمة المحظورين

📊 أوامر الإدارة:
/stats - إحصائيات البوت
/groups - قائمة القروبات
/log - سجل النشاطات"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    await update.message.reply_text(HELP_MESSAGE)


help_handler = CommandHandler("help", help_command)
