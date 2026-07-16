from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from bot.config import is_admin
from bot.services.database import (
    add_auto_response, get_all_auto_responses, remove_auto_response,
    add_question, get_all_questions, delete_question,
    get_all_news, get_news_by_id, delete_news,
    ban_user, get_all_banned, is_banned,
    get_active_channel_groups, log_activity
)
from bot.services.news_publisher import wrap_links_in_blockquote
import logging

logger = logging.getLogger(__name__)


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

**📰 المنشورات:**
/n add - إضافة منشور
/n list - عرض المنشورات
/n del \[رقم\] - حذف منشور
/n edit \[رقم\] - تعديل عنوان/محتوى المنشور
/n republish \[رقم\] - إعادة نشر المنشور
/n delete-all - حذف جميع المنشورات
/n channel-del \[رقم\] - حذف من القناة فقط

**👤 إدارة المستخدمين:**
/ban \[رقم\] \[سبب\] - حظر مستخدم
/unban \[رقم\] - رفع الحظر
/banned - قائمة المحظورين

**📊 عام:**
/stats - إحصائيات البوت
/groups - قائمة القروبات
/broadcast \[رسالة\] - إرسال للجميع"""

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


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
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


async def response_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    responses = await get_all_auto_responses()
    if not responses:
        await update.message.reply_text("📭 لا توجد ردود تلقائية", disable_web_page_preview=True)
        return

    text = "📋 **الردود التلقائية:**\n\n"
    for r in responses[:30]:
        status = "✅" if r.is_active else "❌"
        text += f"{status} `{r.id}` - 🔑 {r.keyword} 📰 منشور: {r.news_id or 'بدون'}\n"

    if len(responses) > 30:
        text += f"\n... و {len(responses) - 30} رد آخر"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def response_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ الطريقة الصحيحة:\n/r add \[كلمة\] \[رد\]",
            disable_web_page_preview=True
        )
        return

    keyword = context.args[0]
    response_text = ' '.join(context.args[1:])
    if not response_text:
        await update.message.reply_text("❌ يجب تحديد نص الرد بعد الكلمة المفتاحية", disable_web_page_preview=True)
        return

    try:
        await add_auto_response(keyword=keyword, response=response_text, created_by=update.effective_user.id)
        await update.message.reply_text(f"✅ تمت إضافة الرد\n🔑 الكلمة: {keyword}", disable_web_page_preview=True)
        await log_activity("add_response", f"Keyword: {keyword}", update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إضافة الرد: {str(e)}", disable_web_page_preview=True)


async def response_add_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة لإضافة رد تلقائي", disable_web_page_preview=True)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ الطريقة الصحيحة:\nالرد على رسالة بـ /r add \[كلمة\]",
            disable_web_page_preview=True
        )
        return

    keyword = context.args[0]
    replied = update.message.reply_to_message
    response_text = replied.text or replied.caption or ""

    if not response_text and not (replied.photo or replied.video or replied.document or replied.voice or replied.audio):
        await update.message.reply_text("❌ الرسالة المُشار إليها لا تحتوي على محتوى", disable_web_page_preview=True)
        return

    file_url = None
    file_type = None
    try:
        if replied.photo:
            file_obj = replied.photo[-1]
            file_type = "photo"
            tg_file = await file_obj.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            from bot.services.cloud_storage import upload_image
            file_url = upload_image(bytes(file_bytes), folder="kku-bot/responses")
        elif replied.video:
            file_type = "video"
            tg_file = await replied.video.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            from bot.services.cloud_storage import upload_file
            file_url = upload_file(bytes(file_bytes), folder="kku-bot/responses")
        elif replied.document:
            file_type = "document"
            tg_file = await replied.document.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            from bot.services.cloud_storage import upload_raw
            file_url = upload_raw(bytes(file_bytes), filename=replied.document.file_name or "file", folder="kku-bot/responses")
        elif replied.voice or replied.audio:
            file_type = "document"
            obj = replied.voice or replied.audio
            tg_file = await obj.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            from bot.services.cloud_storage import upload_raw
            file_url = upload_raw(bytes(file_bytes), filename="audio", folder="kku-bot/responses")
    except Exception:
        pass

    try:
        await add_auto_response(
            keyword=keyword,
            response=response_text or "تم الرد عبر المنشور",
            created_by=update.effective_user.id,
            file_url=file_url,
            file_type=file_type,
        )
        file_info = f"\n📎 مرفق: {file_type}" if file_type else ""
        await update.message.reply_text(f"✅ تمت إضافة الرد\n🔑 الكلمة: {keyword}{file_info}", disable_web_page_preview=True)
        await log_activity("add_response", f"Keyword: {keyword}", update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إضافة الرد: {str(e)}", disable_web_page_preview=True)


async def response_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/r del \[رقم\]", disable_web_page_preview=True)
        return

    try:
        response_id = int(context.args[0])
        await remove_auto_response(response_id)
        await update.message.reply_text(f"✅ تمت حذف الرد رقم {response_id}", disable_web_page_preview=True)
        await log_activity("delete_response", f"ID: {response_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل حذف الرد: {str(e)}", disable_web_page_preview=True)


async def response_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/r search \[كلمة\]", disable_web_page_preview=True)
        return

    query = ' '.join(context.args)
    responses = await get_all_auto_responses()
    results = [r for r in responses if query.lower() in r.keyword.lower()]

    if not results:
        await update.message.reply_text(f"🔍 لا توجد نتائج لـ: {query}", disable_web_page_preview=True)
        return

    text = f"🔍 **نتائج البحث لـ:** {query}\n\n"
    for r in results[:10]:
        text += f"`{r.id}` - 🔑 {r.keyword}\n📰 منشور: {r.news_id or 'بدون'}\n\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


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
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
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
            "اضافه سؤال [سؤال] [كلمات مفتاحية] [رقم المنشور]",
            disable_web_page_preview=True
        )
        return

    parts = args_text.rsplit(None, 2)
    if len(parts) < 3:
        await update.message.reply_text("❌ يجب تحديد: السؤال + كلمات مفتاحية + رقم المنشور", disable_web_page_preview=True)
        return

    question_text, keywords, news_id_str = parts[0], parts[1], parts[2]

    try:
        news_id = int(news_id_str)
    except ValueError:
        await update.message.reply_text("❌ رقم المنشور يجب أن يكون رقماً صحيحاً", disable_web_page_preview=True)
        return

    try:
        await add_question(
            question=question_text,
            answer="تم الرد عبر المنشور",
            category="عام",
            keywords=keywords,
            news_id=news_id
        )
        await update.message.reply_text(f"✅ تمت إضافة السؤال\n🔗 المنشور المرتبط: {news_id}", disable_web_page_preview=True)
        await log_activity("add_question", f"News ID: {news_id}", update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إضافة السؤال: {str(e)}", disable_web_page_preview=True)


async def question_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = await get_all_questions()
    if not questions:
        await update.message.reply_text("📭 لا توجد أسئلة شائعة", disable_web_page_preview=True)
        return

    text = "❓ **الاسئلة الشائعة:**\n\n"
    for q in questions[:20]:
        text += f"`{q.id}` - 📁 {q.category or 'عام'}\n💬 {q.question[:40]}...\n\n"

    if len(questions) > 20:
        text += f"\n... و {len(questions) - 20} سؤال آخر"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def question_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/q del \[رقم\]", disable_web_page_preview=True)
        return

    try:
        question_id = int(context.args[0])
        await delete_question(question_id)
        await update.message.reply_text(f"✅ تمت حذف السؤال رقم {question_id}", disable_web_page_preview=True)
        await log_activity("delete_question", f"ID: {question_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل حذف السؤال: {str(e)}", disable_web_page_preview=True)


async def question_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/q search \[كلمة\]", disable_web_page_preview=True)
        return

    query = ' '.join(context.args)
    questions = await get_all_questions()
    results = [q for q in questions if query.lower() in (q.question or '').lower() or query.lower() in (q.keywords or '').lower()]

    if not results:
        await update.message.reply_text(f"🔍 لا توجد نتائج لـ: {query}", disable_web_page_preview=True)
        return

    text = f"🔍 **نتائج البحث لـ:** {query}\n\n"
    for q in results[:10]:
        text += f"`{q.id}` - 💬 {q.question[:50]}...\n📝 {q.answer[:50]}...\n\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


# ==================== المنشورات ====================

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
    elif sub_command in ["edit", "تعديل"]:
        await news_edit(update, context)
    elif sub_command in ["republish", "إعادة نشر"]:
        await news_republish(update, context)
    elif sub_command in ["delete-all", "حذف الكل"]:
        await news_delete_all(update, context)
    elif sub_command in ["channel-del", "حذف القناة"]:
        await news_channel_del(update, context)
    else:
        await update.message.reply_text(
            "❌ اوامر المنشورات:\n"
            "/n add - إضافة منشور\n"
            "/n del \[رقم\] - حذف منشور\n"
            "/n list - عرض المنشورات\n"
            "/n edit \[رقم\] - تعديل المنشور\n"
            "/n republish \[رقم\] - إعادة نشر المنشور\n"
            "/n delete-all - حذف جميع المنشورات\n"
            "/n channel-del \[رقم\] - حذف من القناة فقط",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


async def news_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "📰 لإضافة منشور:\n"
        "1. ارسل العنوان كرسالة\n"
        "2. رد عليها بالمحتوى\n"
        "3. ارفق الصورة أو الملف اختيارياً\n"
        "4. اكتب:\n/منشور اضافه\n\n"
        "💡 يمكنك أيضاً استخدام الداشبورد من الويب",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def news_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    news = await get_all_news()
    if not news:
        await update.message.reply_text("📭 لا توجد منشورات", disable_web_page_preview=True)
        return

    text = "📰 **المنشورات:**\n\n"
    for n in news[:15]:
        status = "✅" if n.is_published else "📝"
        text += f"{status} `{n.id}` - {n.content[:30]}\n"

    if len(news) > 15:
        text += f"\n... و {len(news) - 15} منشور آخر"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def news_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/منشور حذف \[رقم\]", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    try:
        news_id = int(context.args[0])
        await delete_news(news_id)
        await update.message.reply_text(f"✅ تمت حذف المنشور رقم {news_id}", disable_web_page_preview=True)
        await log_activity("delete_news", f"ID: {news_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل حذف المنشور: {str(e)}", disable_web_page_preview=True)


async def news_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/منشور تعديل \[رقم\]", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    try:
        news_id = int(context.args[0])
        await update.message.reply_text(
            f"📝 تعديل المنشور رقم {news_id}:\n"
            "1. ارسل العنوان الجديد كرسالة\n"
            "2. رد عليها بالمحتوى الجديد\n"
            "3. ارفق صورة جديدة اختيارياً",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        await log_activity("edit_news", f"ID: {news_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)


async def news_republish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/منشور إعادة نشر \[رقم\]", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    try:
        news_id = int(context.args[0])
        await update.message.reply_text(f"✅ تمت إعادة نشر المنشور رقم {news_id}", disable_web_page_preview=True)
        await log_activity("republish_news", f"ID: {news_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إعادة نشر المنشور: {str(e)}", disable_web_page_preview=True)


async def news_delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        news = await get_all_news()
        count = len(news)
        for n in news:
            await delete_news(n.id)
        await update.message.reply_text(f"✅ تم حذف جميع المنشورات ({count} منشور)", disable_web_page_preview=True)
        await log_activity("delete_all_news", f"Count: {count}", update.effective_user.id)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل حذف المنشورات: {str(e)}", disable_web_page_preview=True)


async def news_channel_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/منشور حذف القناة \[رقم\]", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    try:
        news_id = int(context.args[0])
        await update.message.reply_text(f"✅ تم حذف المنشور رقم {news_id} من القناة فقط", disable_web_page_preview=True)
        await log_activity("channel_del_news", f"ID: {news_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل حذف المنشور من القناة: {str(e)}", disable_web_page_preview=True)


# ==================== إدارة المستخدمين ====================

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "❌ الطريقة الصحيحة:\n/حظر \[رقم\] \[سبب\]",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return

    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "لا يوجد سبب"

        await ban_user(user_id, reason, update.effective_user.id)
        await update.message.reply_text(f"🚫 تم حظر المستخدم `{user_id}`\n📋 السبب: {reason}", disable_web_page_preview=True)
        await log_activity("ban_user", f"User: {user_id}, Reason: {reason}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل الحظر: {str(e)}", disable_web_page_preview=True)


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/الغاء\_حظر \[رقم\]", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    try:
        user_id = int(context.args[0])
        from bot.services.database import async_session
        from sqlalchemy import delete as sql_delete
        from bot.models.models import BannedUser

        async with async_session() as session:
            await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == user_id))
            await session.commit()

        groups = await get_active_channel_groups()
        unbanned_count = 0
        for group in groups:
            try:
                await context.bot.unban_chat_member(chat_id=group.chat_id, user_id=user_id)
                unbanned_count += 1
            except Exception:
                pass

        await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم `{user_id}` من {unbanned_count} مجموعة", disable_web_page_preview=True)
        await log_activity("unban_user", f"User: {user_id}", update.effective_user.id)
    except ValueError:
        await update.message.reply_text("❌ يجب إدخال رقم صحيح", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل رفع الحظر: {str(e)}", disable_web_page_preview=True)


async def banned_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    banned = await get_all_banned()
    if not banned:
        await update.message.reply_text("✅ لا يوجد محظورين", disable_web_page_preview=True)
        return

    text = "🚫 **قائمة المحظورين:**\n\n"
    for b in banned[:20]:
        text += f"`{b.telegram_id}` - {b.reason or 'لا يوجد سبب'}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


# ==================== عام ====================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    from bot.services.database import async_session
    from sqlalchemy import select, func
    from bot.models.models import User, ChannelGroup, Question, News

    async with async_session() as session:
        users = await session.execute(select(func.count(User.id)))
        groups = await session.execute(select(func.count(ChannelGroup.id)))
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
📰 المنشورات: {total_news}"""

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    groups = await get_active_channel_groups()
    if not groups:
        await update.message.reply_text("📭 لا توجد قروبات مسجلة", disable_web_page_preview=True)
        return

    text = "👥 **القروبات:**\n\n"
    for g in groups[:20]:
        status = "✅" if g.is_active else "❌"
        text += f"{status} `{g.chat_id}` - {g.title or 'بدون عنوان'}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❌ الطريقة الصحيحة:\n/اذاعة \[رسالة\]", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    message = ' '.join(context.args)
    groups = await get_active_channel_groups()

    if not groups:
        await update.message.reply_text("📭 لا توجد قروبات لإرسال الرسالة", disable_web_page_preview=True)
        return

    sent = 0
    failed = 0

    for group in groups:
        try:
            await context.bot.send_message(chat_id=group.chat_id, text=wrap_links_in_blockquote(message), parse_mode='HTML', disable_web_page_preview=True)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ تم الإرسال\n📤 نجح: {sent}\n❌ فشل: {failed}", disable_web_page_preview=True)
    await log_activity("broadcast", f"Sent: {sent}, Failed: {failed}", update.effective_user.id)
