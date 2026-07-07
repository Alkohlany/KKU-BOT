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
/news - عرض الأخبار
/questions - البحث في الأسئلة
/plans - خطط الدراسة

👨‍💼 **أوامر المشرفين:**
/رد - أوامر الردود التلقائية
/سؤال - أوامر الأسئلة الشائعة
/خبر - أوامر الأخبار
/احصائيات - إحصائيات البوت
/قروبات - قائمة القروبات
/اذاعة - إرسال رسالة للجميع

🛡️ **أوامر الحماية:**
/حظر - حظر مستخدم
/الغاء\_حظر - رفع الحظر
/قائمة\_الحظر - قائمة المحظورين"""

ADMIN_HELP_MESSAGE = """⚙️ **اوامر الادمن المتقدمة**

**📋 الردود التلقائية:**
/رد اضف \[كلمة\] \[رد\] - إضافة رد جديد
/رد احذف \[رقم\] - حذف رد
/رد قائمة - عرض جميع الردود
/رد بحث \[كلمة\] - البحث في الردود

**❓ الاسئلة الشائعة:**
/سؤال اضف \[قسم\] - إضافة سؤال (بالرد على رسالة)
/سؤال احذف \[رقم\] - حذف سؤال
/سؤال قائمة - عرض الاسئلة
/سؤال بحث \[كلمة\] - البحث في الاسئلة

**📰 الاخبار:**
/خبر اضافه - إضافة خبر
/خبر قائمة - عرض الاخبار
/خبر حذف \[رقم\] - حذف خبر

**👤 إدارة المستخدمين:**
/حظر \[رقم\] \[سبب\] - حظر مستخدم
/الغاء\_حظر \[رقم\] - رفع الحظر
/قائمة\_الحظر - قائمة المحظورين

**📊 عام:**
/احصائيات - إحصائيات البوت
/قروبات - قائمة القروبات
/اذاعة \[رسالة\] - إرسال للجميع"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text(ADMIN_HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)


help_handler = CommandHandler("help", help_command)
