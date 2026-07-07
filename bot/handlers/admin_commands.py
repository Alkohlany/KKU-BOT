from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from bot.config import ADMIN_IDS
from bot.services.database import (
    add_auto_response, get_all_auto_responses, remove_auto_response,
    add_question, get_all_questions, delete_question,
    get_all_news, delete_news,
    ban_user, get_all_banned, is_banned,
    get_all_groups, log_activity
)
import logging

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ==================== القائمة الرئيسية ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    text = """⚙️ **اوامر الادمن**

**📋 الردود التلقائية:**
/رد اضف \[كلمة\] \[رد\] - إضافة رد جديد
/رد احذف \[رقم\] - حذف رد
/رد قائمة - عرض جميع الردود
/رد بحث \[كلمة\] - البحث في الردود

**❓ الاسئلة الشائعة:**
/سؤال اضف - إضافة سؤال (بالرد على رسالة)
/سؤال احذف \[رقم\] - حذف سؤال
/سؤال قائمة - عرض الاسئلة
/سؤال بحث \[كلمة\] - البحث في الاسئلة

**📰 الاخبار:**
/خبر اضافه - إضافة خبر (بالرد على رسالة)
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

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ==================== الردود التلقائية ====================

async def response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await response_list(update, context)
        return

    sub_command = context.args[0].lower()
    context.args = context.args[1:]

    if sub_command == "اضف":
        if update.message.reply_to_message:
            await response_add_reply(update, context)
        else:
            await response_add(update, context)
    elif sub_command == "احذف":
        await response_delete(update, context)
    elif sub_command == "قائمة":
        await response_list(update, context)
    elif sub_command == "بحث":
        await response_search(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر الردود:\n"
            "/رد اضف \[كلمة\] \[رد\] - إضافة رد\n"
            "/رد احذف \[رقم\] - حذف رد\n"
            "/رد قائمة - عرض الردود\n"
            "/رد بحث \[كلمة\] - البحث في الردود",
            parse_mode=ParseMode.MARKDOWN
        )


# ==================== الاسئلة الشائعة ====================

async def question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await question_list(update, context)
        return

    sub_command = context.args[0].lower()
    context.args = context.args[1:]

    if sub_command == "اضف":
        await question_add(update, context)
    elif sub_command == "احذف":
        await question_delete(update, context)
    elif sub_command == "قائمة":
        await question_list(update, context)
    elif sub_command == "بحث":
        await question_search(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر الاسئلة:\n"
            "/سؤال اضف \[قسم\] - إضافة سؤال (بالرد على رسالة)\n"
            "/سؤال احذف \[رقم\] - حذف سؤال\n"
            "/سؤال قائمة - عرض الاسئلة\n"
            "/سؤال بحث \[كلمة\] - البحث في الاسئلة",
            parse_mode=ParseMode.MARKDOWN
        )


async def question_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ الطريقة الصحيحة:\n"
            "1. ارسل السؤال كرسالة\n"
            "2.رد عليها بالإجابة\n"
            "3.اكتب:\n/سؤال اضف \[قسم\]\n\n"
            "💡 القسم اختياري (مثال: تسجيل، رسوم، مواد)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    category = context.args[0] if context.args else "عام"
    question_text = update.message.reply_to_message.text
    answer_text = update.message.text.replace('/سؤال اضف', '').replace(category, '').strip()

    if not answer_text:
        await update.message.reply_text("❌ يجب كتابة الإجابة بعد الأمر")
        return

    try:
        await add_question(
            question=question_text,
            answer=answer_text,
            category=category
        )
        await update.message.reply_text(f"✅ تمت إضافة السؤال\n📁 القسم: {category}")
        await log_activity("add_question", f"Category: {category}", update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إضافة السؤال: {str(e)}")


# ==================== الاخبار ====================

async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await news_list(update, context)
        return

    sub_command = context.args[0].lower()
    context.args = context.args[1:]

    if sub_command in ["اضافه", "اضافة", "add"]:
        await news_add(update, context)
    elif sub_command in ["حذف", "delete"]:
        await news_delete(update, context)
    elif sub_command in ["قائمة", "list"]:
        await news_list(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر الاخبار:\n"
            "/خبر اضافه - إضافة خبر\n"
            "/خبر حذف \[رقم\] - حذف خبر\n"
            "/خبر قائمة - عرض الاخبار",
            parse_mode=ParseMode.MARKDOWN
        )


async def news_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "📰 لإضافة خبر:\n"
        "1. ارسل العنوان كرسالة\n"
        "2. رد عليها بالمحتوى\n"
        "3. ارفق الصورة أو الملف اختيارياً\n"
        "4. اكتب:\n/خبر اضافه\n\n"
        "💡 يمكنك أيضاً استخدام الداشبورد من الويب",
        parse_mode=ParseMode.MARKDOWN
    )


async def news_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    news = await get_all_news()
    if not news:
        await update.message.reply_text("📭 لا توجد أخبار")
        return

    text = "📰 **الاخبار:**\n\n"
    for n in news[:15]:
        status = "✅" if n.is_published else "📝"
        text += f"{status} `{n.id}` - {n.title[:30]}\n"

    if len(news) > 15:
        text += f"\n... و {len(news) - 15} خبر آخر"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def news_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/خبر حذف \[رقم\]", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        news_id = int(context.args[0])
        await delete_news(news_id)
        await update.message.reply_text(f"✅ تمت حذف الخبر رقم {news_id}")
        await log_activity("delete_news", f"ID: {news_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل حذف الخبر: {str(e)}")


# ==================== إدارة المستخدمين ====================

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "❌ الطريقة الصحيحة:\n/حظر \[رقم\] \[سبب\]",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "لا يوجد سبب"

        await ban_user(user_id, reason, update.effective_user.id)
        await update.message.reply_text(f"🚫 تم حظر المستخدم `{user_id}`\n📋 السبب: {reason}")
        await log_activity("ban_user", f"User: {user_id}, Reason: {reason}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل الحظر: {str(e)}")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/الغاء\_حظر \[رقم\]", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        user_id = int(context.args[0])
        from bot.services.database import async_session
        from sqlalchemy import delete as sql_delete
        from bot.models.models import BannedUser

        async with async_session() as session:
            await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == user_id))
            await session.commit()

        await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم `{user_id}`")
        await log_activity("unban_user", f"User: {user_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل رفع الحظر: {str(e)}")


async def banned_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    banned = await get_all_banned()
    if not banned:
        await update.message.reply_text("✅ لا يوجد محظورين")
        return

    text = "🚫 **قائمة المحظورين:**\n\n"
    for b in banned[:20]:
        text += f"`{b.telegram_id}` - {b.reason or 'لا يوجد سبب'}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ==================== عام ====================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    from bot.services.database import async_session
    from sqlalchemy import select, func
    from bot.models.models import User, Group, Question, News

    async with async_session() as session:
        users = await session.execute(select(func.count(User.id)))
        groups = await session.execute(select(func.count(Group.id)))
        questions = await session.execute(select(func.count(Question.id)))
        news = await session.execute(select(func.count(News.id)))

        total_users = users.scalar()
        total_groups = groups.scalar()
        total_questions = questions.scalar()
        total_news = news.scalar()

    text = f"""📊 **إحصائيات البوت:**

👥 المستخدمين: {total_users}
👥 القروبات: {total_groups}
❓ الاسئلة: {total_questions}
📰 الاخبار: {total_news}"""

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    groups = await get_all_groups()
    if not groups:
        await update.message.reply_text("📭 لا توجد قروبات مسجلة")
        return

    text = "👥 **القروبات:**\n\n"
    for g in groups[:20]:
        status = "✅" if g.is_active else "❌"
        text += f"{status} `{g.chat_id}` - {g.title or 'بدون عنوان'}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/اذاعة \[رسالة\]", parse_mode=ParseMode.MARKDOWN)
        return

    message = ' '.join(context.args)
    groups = await get_all_groups()

    if not groups:
        await update.message.reply_text("📭 لا توجد قروبات لإرسال الرسالة")
        return

    sent = 0
    failed = 0

    for group in groups:
        try:
            await context.bot.send_message(chat_id=group.chat_id, text=message)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ تم الإرسال\n📤 نجح: {sent}\n❌ فشل: {failed}")
    await log_activity("broadcast", f"Sent: {sent}, Failed: {failed}", update.effective_user.id)


# ==================== تسجيل الاوامر ====================

def get_admin_handlers():
    return [
        CommandHandler("ادمن", admin_command),
        CommandHandler("رد", response_handler),
        CommandHandler("سؤال", question_handler),
        CommandHandler("خبر", news_handler),
        CommandHandler("احصائيات", stats_command),
        CommandHandler("قروبات", groups_command),
        CommandHandler("اذاعة", broadcast_command),
        CommandHandler("حظر", ban_command),
        CommandHandler("الغاء_حظر", unban_command),
        CommandHandler("قائمة_الحظر", banned_list),
    ]
