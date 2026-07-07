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
/r add \[كلمة\] \[رد\] - إضافة رد جديد
/r del \[رقم\] - حذف رد
/r list - عرض جميع الردود
/r search \[كلمة\] - البحث في الردود

**❓ الاسئلة الشائعة:**
/q add \[قسم\] - إضافة سؤال (بالرد على رسالة)
/q del \[رقم\] - حذف سؤال
/q list - عرض الاسئلة
/q search \[كلمة\] - البحث في الاسئلة

**📰 الاخبار:**
/n add - إضافة خبر
/n list - عرض الاخبار
/n del \[رقم\] - حذف خبر

**👤 إدارة المستخدمين:**
/ban \[رقم\] \[سبب\] - حظر مستخدم
/unban \[رقم\] - رفع الحظر
/banned - قائمة المحظورين

**📊 عام:**
/stats - إحصائيات البوت
/groups - قائمة القروبات
/broadcast \[رسالة\] - إرسال للجميع"""

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

    if sub_command in ["add", "اضف"]:
        if update.message.reply_to_message:
            await response_add_reply(update, context)
        else:
            await response_add(update, context)
    elif sub_command in ["del", "احذف"]:
        await response_delete(update, context)
    elif sub_command in ["list", "قائمة"]:
        await response_list(update, context)
    elif sub_command in ["search", "بحث"]:
        await response_search(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر الردود:\n"
            "/r add \[كلمة\] \[رد\] - إضافة رد\n"
            "/r del \[رقم\] - حذف رد\n"
            "/r list - عرض الردود\n"
            "/r search \[كلمة\] - البحث في الردود",
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

    if sub_command in ["add", "اضف"]:
        await question_add(update, context)
    elif sub_command in ["del", "احذف"]:
        await question_delete(update, context)
    elif sub_command in ["list", "قائمة"]:
        await question_list(update, context)
    elif sub_command in ["search", "بحث"]:
        await question_search(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر الاسئلة:\n"
            "/q add \[قسم\] - إضافة سؤال (بالرد على رسالة)\n"
            "/q del \[رقم\] - حذف سؤال\n"
            "/q list - عرض الاسئلة\n"
            "/q search \[كلمة\] - البحث في الاسئلة",
            parse_mode=ParseMode.MARKDOWN
        )


async def question_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    raw_text = update.message.text
    cmd_variants = ["/q add ", "/q add", "/سؤال اضف ", "/سؤال اضف"]
    args_text = raw_text
    for cmd in cmd_variants:
        if raw_text.startswith(cmd):
            args_text = raw_text[len(cmd):]
            break

    args_text = args_text.strip()

    if not args_text:
        await update.message.reply_text(
            "❌ الطريقة الصحيحة:\n"
            "/q add [سؤال] [كلمات مفتاحية] [رقم المنشور]\n\n"
            "💡 مثال:\n"
            "/q add كيف أسجل تسجيل,قوائم 5\n\n"
            "💡 يمكنك أيضاً استخدام:\n"
            "اضافه سؤال [سؤال] [كلمات مفتاحية] [رقم المنشور]"
        )
        return

    parts = args_text.rsplit(None, 2)
    if len(parts) < 3:
        await update.message.reply_text("❌ يجب تحديد: السؤال + كلمات مفتاحية + رقم المنشور")
        return

    question_text, keywords, news_id_str = parts[0], parts[1], parts[2]

    try:
        news_id = int(news_id_str)
    except ValueError:
        await update.message.reply_text("❌ رقم المنشور يجب أن يكون رقماً صحيحاً")
        return

    try:
        await add_question(
            question=question_text,
            answer="تم الرد عبر المنشور",
            category="عام",
            keywords=keywords,
            news_id=news_id
        )
        await update.message.reply_text(f"✅ تمت إضافة السؤال\n🔗 المنشور المرتبط: {news_id}")
        await log_activity("add_question", f"News ID: {news_id}", update.effective_user.id)
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

    if sub_command in ["add", "اضافه", "اضافة"]:
        await news_add(update, context)
    elif sub_command in ["del", "حذف", "delete"]:
        await news_delete(update, context)
    elif sub_command in ["list", "قائمة"]:
        await news_list(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر الاخبار:\n"
            "/n add - إضافة خبر\n"
            "/n del \[رقم\] - حذف خبر\n"
            "/n list - عرض الاخبار",
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
        CommandHandler("admin", admin_command),
        CommandHandler("r", response_handler),
        CommandHandler("q", question_handler),
        CommandHandler("n", news_handler),
        CommandHandler("stats", stats_command),
        CommandHandler("groups", groups_command),
        CommandHandler("broadcast", broadcast_command),
        CommandHandler("ban", ban_command),
        CommandHandler("unban", unban_command),
        CommandHandler("banned", banned_list),
    ]
