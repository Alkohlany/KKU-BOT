from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from bot.middleware.subscription import subscription_required
from bot.config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

HELP_MESSAGE = """📚 أوامر البوت

👤 **أوامر عامة:**
/start - بدء استخدام البوت
/help - عرض هذه الرسالة
/menu - فتح القائمة الرئيسية
/plans - خطط الدراسة
/books - الكتب المتوفرة

👨‍💼 **أوامر المشرفين:**
/r - أوامر الردود التلقائية
/q - أوامر الأسئلة الشائعة
/n - أوامر المنشورات
/stats - إحصائيات البوت
/groups - قائمة القروبات
/broadcast - إرسال رسالة للجميع

🛡️ **أوامر الحماية:**
/ban - حظر مستخدم
/unban - رفع الحظر
/banned - قائمة المحظورين"""

ADMIN_HELP_MESSAGE = r"""⚙️ **اوامر الادمن المتقدمة**

**📋 الردود التلقائية:**
/r add \[كلمة\] \[رد\] - إضافة رد جديد
/r del \[رقم\] - حذف رد
/r list - عرض جميع الردود
/r search \[كلمة\] - البحث في الردود

**❓ الاسئلة الشائعة:**
/q add \[قسم\] - إضافة سؤال (بالرد على رسالة)
/q del \[رقم\] - حذف سؤال
/q list - عرض الاسئلة
/q search \[كلمة\] - البحث في الاسئلة

**📰 المنشورات:**
/n add - إضافة خبر
/n list - عرض المنشورات
/n del \[رقم\] - حذف خبر

**🚫 المحتوى المحظور:**
/spam add \[نص\] - إضافة نص محظور
/spam add بالرد على رسالة - إضافة محتوى الرسالة
/spam del \[رقم\] - حذف نص
/spam list - عرض القائمة

**👤 إدارة المستخدمين:**
/ban \[رقم\] \[سبب\] - حظر مستخدم
/unban \[رقم\] - رفع الحظر
/banned - قائمة المحظورين

**📊 عام:**
/stats - إحصائيات البوت
/groups - قائمة القروبات
/broadcast \[رسالة\] - إرسال للجميع"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text(ADMIN_HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


help_handler = CommandHandler("help", help_command)
