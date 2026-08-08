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
/help - عرض هذه الرسالة"""

ADMIN_HELP_MESSAGE = """**⚙️ لوحة تحكم الأدمن**
/admin - فتح لوحة التحكم

⚙️ أوامر الأدمن في القروبات
📋 الردود التلقائية:
اضافه رد [كلمة] - إضافة رد (يعرض قائمة المنشورات)
احذف رد [رقم] - حذف رد
قائمة الردود - عرض جميع الردود
بحث في الردود [كلمة] - بحث في الردود

❓ الأسئلة الشائعة:
اضافه سؤال [سؤال] [كلمات] [رقم] - إضافة سؤال
احذف سؤال [رقم] - حذف سؤال
قائمة الاسئلة - عرض الأسئلة
بحث في الاسئلة [كلمة] - بحث

📰 المنشورات:
اضافه منشور - إضافة منشور
احذف منشور [رقم] - حذف منشور
قائمة المنشورات - عرض المنشورات

🚫 المحتوى المحظور:
اضف محتوى محظور - إضافة نص محظور
قائمة المحظورين - عرض المحظورين

👤 إدارة المستخدمين:
حظر [رقم] [سبب] - حظر مستخدم
الغاء حظر [رقم] - رفع الحظر
الاحصائيات - إحصائيات البوت
القروبات - قائمة القروبات
اذاعة [رسالة] - إرسال رسالة للجميع"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text(ADMIN_HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


help_handler = CommandHandler("help", help_command)
