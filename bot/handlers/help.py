from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from bot.middleware.subscription import subscription_required
from bot.config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

HELP_MESSAGE = """📚 أوامر البوت

/start - بدء استخدام البوت
/menu - فتح القائمة الرئيسية
/plans - خطط الدراسة
/books - الكتب المتوفرة
/help - عرض هذه الرسالة

👨‍💼 للأدمن: اكتب /admin في الخاص"""

ADMIN_HELP_MESSAGE = """⚙️ لوحة تحكم الأدمن

💡 للأسهل: اكتب /admin

📋 الردود: اضافه رد / احذف رد / قائمة الردود
❓ الأسئلة: اضافه سؤال / احذف سؤال / قائمة الاسئلة
📰 المنشورات: اضافه منشور / احذف منشور / قائمة المنشورات
🚫 المحظور: اضف محتوى محظور / قائمة المحظورين
👤 المستخدمين: حظر / الغاء حظر / قائمة المحظورين
📊 الإحصائيات: الاحصائيات / القروبات / اذاعة"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text(ADMIN_HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


help_handler = CommandHandler("help", help_command)
