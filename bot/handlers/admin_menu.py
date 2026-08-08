"""قائمة الأوامر التفاعلية للأدمن بالداخلية."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from bot.config import is_admin
from bot.services.database import (
    get_all_auto_responses, remove_auto_response,
    get_all_questions, delete_question,
    get_all_news, get_news_by_id, delete_news,
    get_all_banned, ban_user, is_banned,
    get_active_channel_groups, log_activity,
    save_spam_pattern, get_all_spam_patterns, delete_spam_pattern,
    async_session, add_auto_response, add_question, add_news
)
from sqlalchemy import select, func
from bot.models.models import User, ChannelGroup, Question, News
import logging

logger = logging.getLogger(__name__)

# ==================== القائمة الرئيسية ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "⚙️ لوحة تحكم الأدمن\nاختر القسم:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "⚙️ لوحة تحكم الأدمن\nاختر القسم:",
            reply_markup=main_menu_keyboard()
        )

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 الردود", callback_data="admin:responses"),
         InlineKeyboardButton("❓ الأسئلة", callback_data="admin:questions")],
        [InlineKeyboardButton("📰 المنشورات", callback_data="admin:news"),
         InlineKeyboardButton("🚫 المحظور", callback_data="admin:spam")],
        [InlineKeyboardButton("👤 المستخدمين", callback_data="admin:users"),
         InlineKeyboardButton("📊 الإحصائيات", callback_data="admin:stats")],
        [InlineKeyboardButton("📢 إذاعة", callback_data="admin:broadcast"),
         InlineKeyboardButton("👥 القروبات", callback_data="admin:groups")],
    ])

# ==================== Callback Handler ====================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك", show_alert=True)
        return

    data = query.data
    await query.answer()

    # ==================== الرجوع للقائمة الرئيسية ====================
    if data == "admin:main":
        await query.edit_message_text(
            "⚙️ لوحة تحكم الأدمن\nاختر القسم:",
            reply_markup=main_menu_keyboard()
        )
        return

    # ==================== الردود ====================
    if data == "admin:responses":
        await query.edit_message_text(
            "📋 الردود التلقائية",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة رد", callback_data="admin:resp:add"),
                 InlineKeyboardButton("📋 قائمة الردود", callback_data="admin:resp:list")],
                [InlineKeyboardButton("🔍 بحث", callback_data="admin:resp:search"),
                 InlineKeyboardButton("❌ حذف رد", callback_data="admin:resp:del")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")],
            ])
        )

    elif data == "admin:resp:list":
        responses = await get_all_auto_responses()
        if not responses:
            text = "📭 لا توجد ردود تلقائية"
        else:
            text = "📋 الردود التلقائية:\n\n"
            for r in responses[:20]:
                status = "✅" if r.is_active else "❌"
                text += f"{status} `{r.id}` - 🔑 {r.keyword}\n"
            if len(responses) > 20:
                text += f"\n... و {len(responses) - 20} رد آخر"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:responses")]
        ]))

    elif data == "admin:resp:add":
        context.user_data['admin_state'] = 'resp_add_keyword'
        await query.edit_message_text(
            "📝 أرسل الكلمة المفتاحية للرد الجديد",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:responses")]
            ])
        )

    elif data == "admin:resp:search":
        context.user_data['admin_state'] = 'resp_search'
        await query.edit_message_text(
            "🔍 أرسل كلمة للبحث في الردود",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:responses")]
            ])
        )

    elif data == "admin:resp:del":
        context.user_data['admin_state'] = 'resp_del'
        await query.edit_message_text(
            "❌ أرسل رقم الرد للحذف",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:responses")]
            ])
        )

    # ==================== الأسئلة ====================
    elif data == "admin:questions":
        await query.edit_message_text(
            "❓ الأسئلة الشائعة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة سؤال", callback_data="admin:q:add"),
                 InlineKeyboardButton("📋 قائمة الأسئلة", callback_data="admin:q:list")],
                [InlineKeyboardButton("🔍 بحث", callback_data="admin:q:search"),
                 InlineKeyboardButton("❌ حذف سؤال", callback_data="admin:q:del")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")],
            ])
        )

    elif data == "admin:q:list":
        questions = await get_all_questions()
        if not questions:
            text = "📭 لا توجد أسئلة شائعة"
        else:
            text = "❓ الأسئلة الشائعة:\n\n"
            for q in questions[:20]:
                text += f"`{q.id}` - 💬 {q.question[:40]}...\n"
            if len(questions) > 20:
                text += f"\n... و {len(questions) - 20} سؤال آخر"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:questions")]
        ]))

    elif data == "admin:q:add":
        context.user_data['admin_state'] = 'q_add_question'
        await query.edit_message_text(
            "📝 أرسل نص السؤال",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:questions")]
            ])
        )

    elif data == "admin:q:search":
        context.user_data['admin_state'] = 'q_search'
        await query.edit_message_text(
            "🔍 أرسل كلمة للبحث في الأسئلة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:questions")]
            ])
        )

    elif data == "admin:q:del":
        context.user_data['admin_state'] = 'q_del'
        await query.edit_message_text(
            "❌ أرسل رقم السؤال للحذف",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:questions")]
            ])
        )

    # ==================== المنشورات ====================
    elif data == "admin:news":
        await query.edit_message_text(
            "📰 المنشورات",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 قائمة المنشورات", callback_data="admin:n:list")],
                [InlineKeyboardButton("❌ حذف منشور", callback_data="admin:n:del")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")],
            ])
        )

    elif data == "admin:n:list":
        news = await get_all_news()
        if not news:
            text = "📭 لا توجد منشورات"
        else:
            text = "📰 المنشورات:\n\n"
            for n in news[:15]:
                status = "✅" if n.is_published else "📝"
                text += f"{status} `{n.id}` - {n.content[:30]}\n"
            if len(news) > 15:
                text += f"\n... و {len(news) - 15} منشور آخر"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:news")]
        ]))

    elif data == "admin:n:del":
        context.user_data['admin_state'] = 'n_del'
        await query.edit_message_text(
            "❌ أرسل رقم المنشور للحذف",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:news")]
            ])
        )

    # ==================== المحتوى المحظور ====================
    elif data == "admin:spam":
        await query.edit_message_text(
            "🚫 إدارة المحتوى المحظور",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة نص محظور", callback_data="admin:sp:add"),
                 InlineKeyboardButton("📋 قائمة المحظورات", callback_data="admin:sp:list")],
                [InlineKeyboardButton("❌ حذف نص", callback_data="admin:sp:del")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")],
            ])
        )

    elif data == "admin:sp:list":
        patterns = await get_all_spam_patterns()
        if not patterns:
            text = "📭 لا توجد أنماط محتوى محظور"
        else:
            text = "🚫 المحتوى المحظور:\n\n"
            for p in patterns[:20]:
                content = p.content[:40] + "..." if len(p.content) > 40 else p.content
                text += f"`{p.id}` - {content}\n"
            if len(patterns) > 20:
                text += f"\n... و {len(patterns) - 20} نمط آخر"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:spam")]
        ]))

    elif data == "admin:sp:add":
        context.user_data['admin_state'] = 'sp_add'
        await query.edit_message_text(
            "📝 أرسل النص المحظور",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:spam")]
            ])
        )

    elif data == "admin:sp:del":
        context.user_data['admin_state'] = 'sp_del'
        await query.edit_message_text(
            "❌ أرسل رقم النمط للحذف",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:spam")]
            ])
        )

    # ==================== إدارة المستخدمين ====================
    elif data == "admin:users":
        await query.edit_message_text(
            "👤 إدارة المستخدمين",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin:u:ban")],
                [InlineKeyboardButton("✅ رفع حظر", callback_data="admin:u:unban")],
                [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="admin:u:list")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")],
            ])
        )

    elif data == "admin:u:list":
        banned = await get_all_banned()
        if not banned:
            text = "✅ لا يوجد محظورين"
        else:
            text = "🚫 المحظورون:\n\n"
            for b in banned[:20]:
                text += f"`{b.telegram_id}` - {b.reason or 'بدون سبب'}\n"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:users")]
        ]))

    elif data == "admin:u:ban":
        context.user_data['admin_state'] = 'u_ban'
        await query.edit_message_text(
            "🚫 أرسل رقم المستخدم للحظر (مع السبب اختيارياً)\nمثال: 12345 سبب الحظر",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:users")]
            ])
        )

    elif data == "admin:u:unban":
        context.user_data['admin_state'] = 'u_unban'
        await query.edit_message_text(
            "✅ أرسل رقم المستخدم لرفع الحظر",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:users")]
            ])
        )

    # ==================== الإحصائيات ====================
    elif data == "admin:stats":
        async with async_session() as session:
            users = await session.execute(select(func.count(User.id)))
            groups = await session.execute(select(func.count(ChannelGroup.id)))
            questions = await session.execute(select(func.count(Question.id)))
            news = await session.execute(select(func.count(News.id)))

            total_users = users.scalar()
            total_groups = groups.scalar()
            total_questions = questions.scalar()
            total_news = news.scalar()

        text = f"""📊 إحصائيات البوت:

👥 المستخدمين: {total_users}
👥 القروبات: {total_groups}
❓ الأسئلة: {total_questions}
📰 المنشورات: {total_news}"""

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")]
        ]))

    # ==================== الإذاعة ====================
    elif data == "admin:broadcast":
        context.user_data['admin_state'] = 'broadcast'
        await query.edit_message_text(
            "📢 أرسل الرسالة للإرسال للجميع",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin:main")]
            ])
        )

    # ==================== القروبات ====================
    elif data == "admin:groups":
        groups = await get_active_channel_groups()
        if not groups:
            text = "📭 لا توجد قروبات مسجلة"
        else:
            text = "👥 القروبات:\n\n"
            for g in groups[:20]:
                status = "✅" if g.is_active else "❌"
                text += f"{status} `{g.chat_id}` - {g.title or 'بدون عنوان'}\n"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin:main")]
        ]))


# ==================== معالجة النصوص (للأفعال متعددة الخطوات) ====================

async def admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if update.effective_chat.type != "private":
        return

    state = context.user_data.get('admin_state')
    if not state:
        return

    text = update.message.text.strip()

    # ==================== الردود ====================
    if state == 'resp_add_keyword':
        context.user_data['resp_keyword'] = text
        context.user_data['admin_state'] = 'resp_add_news'
        news = await get_all_news()
        if not news:
            await update.message.reply_text("❌ لا توجد منشورات. أضف منشوراً أولاً")
            context.user_data.pop('admin_state', None)
            context.user_data.pop('resp_keyword', None)
            return
        msg = "📰 اختر المنشور بالرقم:\n\n"
        for n in news[:10]:
            status = "✅" if n.is_published else "📝"
            msg += f"{status} `{n.id}` - {n.content[:40]}\n"
        msg += "\n💡 أرسل رقم المنشور بعلامة # مثل: #5"
        await update.message.reply_text(msg)
        return

    if state == 'resp_add_news':
        keyword = context.user_data.pop('resp_keyword', None)
        context.user_data.pop('admin_state', None)
        if not text.startswith("#") or not text[1:].isdigit():
            await update.message.reply_text("❌ يجب إرسال رقم بعلامة # مثل: #5")
            return
        news_id = int(text[1:])
        news = await get_news_by_id(news_id)
        if not news:
            await update.message.reply_text(f"❌ المنشور رقم {news_id} غير موجود")
            return
        await add_auto_response(keyword=keyword, response="تم الرد عبر المنشور", created_by=user_id, news_id=news_id)
        await update.message.reply_text(f"✅ تمت إضافة الرد\n🔑 الكلمة: {keyword}\n📰 المنشور: {news_id}")
        await log_activity("add_response", f"Keyword: {keyword}, News: {news_id}", user_id)
        return

    if state == 'resp_search':
        context.user_data.pop('admin_state', None)
        responses = await get_all_auto_responses()
        results = [r for r in responses if text.lower() in r.keyword.lower()]
        if not results:
            await update.message.reply_text(f"🔍 لا توجد نتائج لـ: {text}")
            return
        msg = f"🔍 نتائج البحث لـ: {text}\n\n"
        for r in results[:10]:
            msg += f"`{r.id}` - 🔑 {r.keyword}\n📰 منشور: {r.news_id or 'بدون'}\n\n"
        await update.message.reply_text(msg)
        return

    if state == 'resp_del':
        context.user_data.pop('admin_state', None)
        try:
            resp_id = int(text)
            await remove_auto_response(resp_id)
            await update.message.reply_text(f"✅ تمت حذف الرد رقم {resp_id}")
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح")
        return

    # ==================== الأسئلة ====================
    if state == 'q_add_question':
        context.user_data['q_text'] = text
        context.user_data['admin_state'] = 'q_add_keywords'
        await update.message.reply_text("🔑 أرسل الكلمات المفتاحية (مفصولة بفواصل)")
        return

    if state == 'q_add_keywords':
        context.user_data['q_keywords'] = text
        context.user_data['admin_state'] = 'q_add_news'
        await update.message.reply_text("📰 أرسل رقم المنشور بعلامة # مثل: #5")
        return

    if state == 'q_add_news':
        q_text = context.user_data.pop('q_text', None)
        q_keywords = context.user_data.pop('q_keywords', None)
        context.user_data.pop('admin_state', None)
        if not text.startswith("#") or not text[1:].isdigit():
            await update.message.reply_text("❌ يجب إرسال رقم بعلامة # مثل: #5")
            return
        news_id = int(text[1:])
        news = await get_news_by_id(news_id)
        if not news:
            await update.message.reply_text(f"❌ المنشور رقم {news_id} غير موجود")
            return
        await add_question(question=q_text, answer="تم الرد عبر المنشور", keywords=q_keywords, news_id=news_id)
        await update.message.reply_text(f"✅ تمت إضافة السؤال\n💬 السؤال: {q_text}\n🔑 الكلمات: {q_keywords}\n📰 المنشور: {news_id}")
        await log_activity("add_question", f"Question: {q_text}, News: {news_id}", user_id)
        return

    if state == 'q_search':
        context.user_data.pop('admin_state', None)
        questions = await get_all_questions()
        results = [q for q in questions if text.lower() in (q.question or '').lower() or text.lower() in (q.keywords or '').lower()]
        if not results:
            await update.message.reply_text(f"🔍 لا توجد نتائج لـ: {text}")
            return
        msg = f"🔍 نتائج البحث لـ: {text}\n\n"
        for q in results[:10]:
            msg += f"`{q.id}` - 💬 {q.question[:50]}...\n\n"
        await update.message.reply_text(msg)
        return

    if state == 'q_del':
        context.user_data.pop('admin_state', None)
        try:
            q_id = int(text)
            await delete_question(q_id)
            await update.message.reply_text(f"✅ تمت حذف السؤال رقم {q_id}")
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح")
        return

    # ==================== المنشورات ====================
    if state == 'n_del':
        context.user_data.pop('admin_state', None)
        try:
            news_id = int(text)
            await delete_news(news_id)
            await update.message.reply_text(f"✅ تمت حذف المنشور رقم {news_id}")
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح")
        return

    # ==================== المحتوى المحظور ====================
    if state == 'sp_add':
        context.user_data.pop('admin_state', None)
        await save_spam_pattern(text)
        await update.message.reply_text(f"✅ تمت إضافة النص المحظور\n🚫 النص: {text[:100]}")
        await log_activity("add_spam", f"Content: {text[:100]}", user_id)
        return

    if state == 'sp_del':
        context.user_data.pop('admin_state', None)
        try:
            sp_id = int(text)
            await delete_spam_pattern(sp_id)
            await update.message.reply_text(f"✅ تمت حذف النمط رقم {sp_id}")
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح")
        return

    # ==================== إدارة المستخدمين ====================
    if state == 'u_ban':
        context.user_data.pop('admin_state', None)
        parts = text.split(None, 1)
        try:
            target_id = int(parts[0])
            reason = parts[1] if len(parts) > 1 else "لا يوجد سبب"
            if await is_banned(target_id):
                await update.message.reply_text("⚠️ هذا المستخدم محظور بالفعل")
                return
            await ban_user(target_id, reason, user_id)
            await update.message.reply_text(f"🚫 تم حظر المستخدم `{target_id}`\n📋 السبب: {reason}")
            await log_activity("ban_user", f"User: {target_id}, Reason: {reason}", user_id)
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح")
        return

    if state == 'u_unban':
        context.user_data.pop('admin_state', None)
        try:
            from sqlalchemy import delete as sql_delete
            from bot.models.models import BannedUser
            target_id = int(text)
            async with async_session() as session:
                await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == target_id))
                await session.commit()
            groups = await get_active_channel_groups()
            for group in groups:
                try:
                    await context.bot.unban_chat_member(chat_id=group.chat_id, user_id=target_id)
                except: pass
            await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم `{target_id}`")
            await log_activity("unban_user", f"User: {target_id}", user_id)
        except ValueError:
            await update.message.reply_text("❌ يجب إدخال رقم صحيح")
        return

    # ==================== الإذاعة ====================
    if state == 'broadcast':
        context.user_data.pop('admin_state', None)
        groups = await get_active_channel_groups()
        if not groups:
            await update.message.reply_text("📭 لا توجد قروبات لإرسال الرسالة")
            return
        sent = 0
        failed = 0
        from bot.services.news_publisher import wrap_links_in_blockquote
        for group in groups:
            try:
                await context.bot.send_message(chat_id=group.chat_id, text=wrap_links_in_blockquote(text), parse_mode='HTML', disable_web_page_preview=True)
                sent += 1
            except: failed += 1
        await update.message.reply_text(f"✅ تم الإرسال\n📤 نجح: {sent}\n❌ فشل: {failed}")
        await log_activity("broadcast", f"Sent: {sent}, Failed: {failed}", user_id)
        return


# ==================== التسجيل ====================

admin_panel_command = CommandHandler("admin", admin_panel)
admin_panel_text = MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND & ~filters.REPLY, admin_text_input)
admin_panel_callback = CallbackQueryHandler(admin_callback_handler, pattern=r"^admin:")
