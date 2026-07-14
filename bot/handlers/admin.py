from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.constants import ChatMemberStatus, ParseMode
from bot.config import ADMIN_IDS
from bot.services.cloud_storage import upload_raw, upload_image, upload_file
from bot.services.news_publisher import wrap_links_in_blockquote
from bot.services.database import (
    get_auto_responses_by_source, remove_auto_responses_by_source,
    add_auto_response, get_all_auto_responses, remove_auto_response,
    add_question, get_all_questions, delete_question,
    get_all_news, get_news_by_id, delete_news, add_news,
    ban_user, get_all_banned, is_banned,
    get_active_channel_groups, log_activity, async_session
)
import logging
from sqlalchemy import delete as sql_delete
from bot.models.models import AutoResponse, BannedUser

logger = logging.getLogger(__name__)


def detect_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'photo'
    if ext in ('mp4', 'avi', 'mov', 'mkv'):
        return 'video'
    return 'document'


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def send_admin_message(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str, parse_mode=None):
    try:
        await context.bot.send_message(chat_id=user_id, text=wrap_links_in_blockquote(text), parse_mode=parse_mode, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Failed to send private message to admin {user_id}: {e}")


# ==================== اوامر النص المباشر ====================

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.reply_to_message:
        return

    text = update.message.text.strip()
    user = update.effective_user
    chat = update.effective_chat

    is_chat_admin = False
    try:
        member = await chat.get_member(user.id)
        is_chat_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        pass

    is_bot_admin = user.id in context.bot_data.get('admin_ids', [])

    if not is_chat_admin and not is_bot_admin:
        return

    # ==================== الردود التلقائية ====================
    if text.startswith("اضافه رد") or text.startswith("أضف رد") or text.startswith("اضف رد"):
        try:
            await update.message.delete()
        except: pass
        
        keywords_part = text.replace("اضافه رد", "").replace("أضف رد", "").replace("اضف رد", "").strip()
        
        if not keywords_part:
            await send_admin_message(context, user.id,
                "❌ الطريقة الصحيحة:\n"
                "اضافه رد [كلمة مفتاحية]\n\n"
                "💡 البوت يعرض لك قائمة المنشورات لتختار منها")
            return

        # Check if user is in the middle of selecting a news post
        if 'pending_keyword' in context.user_data:
            await send_admin_message(context, user.id, "❌ أكمل اختيار المنشور أولاً أو اكتب 'إلغاء' للبدء من جديد")
            return

        keyword = keywords_part.strip()
        
        # Fetch all news posts
        news_list = await get_all_news()
        if not news_list:
            await send_admin_message(context, user.id, "❌ لا توجد منشورات متاحة. أضف منشوراً أولاً")
            return

        # Store keyword in user_data for the next step
        context.user_data['pending_keyword'] = keyword
        
        # Show list of news posts
        news_text = "📰 **اختر المنشور بالرد على هذه الرسالة بالرقم:**\n\n"
        for n in news_list[:10]:
            status = "✅" if n.is_published else "📝"
            news_text += f"{status} `{n.id}` - {n.content[:40]}\n"
        
        if len(news_list) > 10:
            news_text += f"\n... و {len(news_list) - 10} منشور آخر"
        
        news_text += "\n\n💡 أرسل رقم المنشور المطلوب"
        
        await send_admin_message(context, user.id, news_text)
        return

    # Handle news selection for adding response
    if 'pending_keyword' in context.user_data and text.isdigit():
        try:
            await update.message.delete()
        except: pass
        
        keyword = context.user_data.pop('pending_keyword')
        news_id = int(text)
        
        # Verify news exists
        news = await get_news_by_id(news_id)
        if not news:
            await send_admin_message(context, user.id, f"❌ المنشور رقم {news_id} غير موجود")
            return
        
        try:
            await add_auto_response(
                keyword=keyword,
                response="تم الرد عبر المنشور",
                created_by=user.id,
                news_id=news_id
            )
            await send_admin_message(context, user.id, f"✅ تمت إضافة الرد\n\n🔑 الكلمة: {keyword}\n📰 المنشور: {news_id} - {news.content[:30]}")
            await log_activity("add_response", f"Keyword: {keyword}, News: {news_id}", user.id)
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل إضافة الرد: {str(e)}")
        return

    # Handle cancel for pending operations
    if text.strip() == "إلغاء" and 'pending_keyword' in context.user_data:
        try:
            await update.message.delete()
        except: pass
        context.user_data.pop('pending_keyword', None)
        await send_admin_message(context, user.id, "✅ تم الإلغاء")
        return

    elif text.startswith("احذف رد") or text.startswith("احذف الرد"):
        try:
            await update.message.delete()
        except: pass
        id_part = text.replace("احذف رد", "").replace("احذف الرد", "").strip()
        
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب كتابة رقم الرد\n\nمثال: احذف رد 5")
            return

        try:
            response_id = int(id_part)
            await remove_auto_response(response_id)
            await send_admin_message(context, user.id, f"✅ تمت حذف الرد رقم {response_id}")
            await log_activity("delete_response", f"ID: {response_id}", user.id)
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل حذف الرد: {str(e)}")

    elif text in ["قائمة الردود", "الردود", "عرض الردود", "جميع الردود"]:
        responses = await get_all_auto_responses()
        if not responses:
            await send_admin_message(context, user.id, "📭 لا توجد ردود تلقائية")
            return

        text_msg = "📋 **الردود التلقائية:**\n\n"
        for r in responses[:30]:
            status = "✅" if r.is_active else "❌"
            text_msg += f"{status} `{r.id}` - 🔑 {r.keyword} 📰 منشور: {r.news_id or 'بدون'}\n"

        if len(responses) > 30:
            text_msg += f"\n... و {len(responses) - 30} رد آخر"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    elif text.startswith("بحث في الردود") or text.startswith("بحث رد"):
        query = text.replace("بحث في الردود", "").replace("بحث رد", "").strip()
        
        if not query:
            await send_admin_message(context, user.id, "❌ يجب كتابة كلمة البحث\n\nمثال: بحث في الردود تسجيل")
            return

        responses = await get_all_auto_responses()
        results = [r for r in responses if query.lower() in r.keyword.lower()]

        if not results:
            await send_admin_message(context, user.id, f"🔍 لا توجد نتائج لـ: {query}")
            return

        text_msg = f"🔍 **نتائج البحث لـ:** {query}\n\n"
        for r in results[:10]:
            text_msg += f"`{r.id}` - 🔑 {r.keyword}\n📰 منشور: {r.news_id or 'بدون'}\n\n"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    # ==================== الاسئلة الشائعة ====================
    elif text.startswith("اضافه سؤال") or text.startswith("أضف سؤال"):
        keywords_part = text.replace("اضافه سؤال", "").replace("أضف سؤال", "").strip()
        
        if not keywords_part:
            await send_admin_message(context, user.id,
                "❌ الطريقة الصحيحة:\n"
                "اضافه سؤال [سؤال] [كلمات مفتاحية] [رقم المنشور]\n\n"
                "💡 مثال:\n"
                "اضافه سؤال كيف أسجل تسجيل,قوائم 5"
            )
            return

        parts = keywords_part.rsplit(None, 1)
        if len(parts) < 2:
            await send_admin_message(context, user.id, "❌ يجب كتابة السؤال والكلمات المفتاحية ورقم المنشور")
            return

        try:
            news_id = int(parts[1])
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح لرقم المنشور")
            return

        remaining = parts[0].strip()
        remaining_parts = remaining.rsplit(None, 1)
        if len(remaining_parts) < 2:
            await send_admin_message(context, user.id, "❌ يجب كتابة السؤال والكلمات المفتاحية\n\nمثال: اضافه سؤال كيف أسجل تسجيل,قوائم 5")
            return

        question_text = remaining_parts[0]
        keywords = remaining_parts[1]

        try:
            await add_question(
                question=question_text,
                answer="تم الرد عبر المنشور",
                keywords=keywords,
                news_id=news_id
            )
            await send_admin_message(context, user.id, f"✅ تمت إضافة السؤال\n\n💬 السؤال: {question_text}\n🔑 الكلمات: {keywords}\n📰 المنشور: {news_id}")
            await log_activity("add_question", f"Question: {question_text}, News: {news_id}", user.id)
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل إضافة السؤال: {str(e)}")

    elif text.startswith("احذف سؤال") or text.startswith("احذف السؤال"):
        try:
            await update.message.delete()
        except: pass
        id_part = text.replace("احذف سؤال", "").replace("احذف السؤال", "").strip()
        
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب كتابة رقم السؤال\n\nمثال: احذف سؤال 5")
            return

        try:
            question_id = int(id_part)
            await delete_question(question_id)
            await send_admin_message(context, user.id, f"✅ تمت حذف السؤال رقم {question_id}")
            await log_activity("delete_question", f"ID: {question_id}", user.id)
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل حذف السؤال: {str(e)}")

    elif text in ["قائمة الاسئلة", "الاسئلة", "عرض الاسئلة", "جميع الاسئلة", "قائمة الأسئلة", "الأسئلة", "عرض الأسئلة"]:
        questions = await get_all_questions()
        if not questions:
            await send_admin_message(context, user.id, "📭 لا توجد أسئلة شائعة")
            return

        text_msg = "❓ **الاسئلة الشائعة:**\n\n"
        for q in questions[:20]:
            text_msg += f"`{q.id}` - 📁 {q.category or 'عام'}\n💬 {q.question[:40]}...\n\n"

        if len(questions) > 20:
            text_msg += f"\n... و {len(questions) - 20} سؤال آخر"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    elif text.startswith("بحث في الاسئلة") or text.startswith("بحث سؤال") or text.startswith("بحث في الأسئلة"):
        query = text.replace("بحث في الاسئلة", "").replace("بحث سؤال", "").replace("بحث في الأسئلة", "").strip()
        
        if not query:
            await send_admin_message(context, user.id, "❌ يجب كتابة كلمة البحث\n\nمثال: بحث في الاسئلة تسجيل")
            return

        questions = await get_all_questions()
        results = [q for q in questions if query.lower() in (q.question or '').lower() or query.lower() in (q.keywords or '').lower()]

        if not results:
            await send_admin_message(context, user.id, f"🔍 لا توجد نتائج لـ: {query}")
            return

        text_msg = f"🔍 **نتائج البحث لـ:** {query}\n\n"
        for q in results[:10]:
            text_msg += f"`{q.id}` - 💬 {q.question[:50]}...\n📝 {q.answer[:50]}...\n\n"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    # ==================== المنشورات ====================
    elif text.startswith("اضافه منشور") or text.startswith("أضف منشور") or text == "اضافه منشور":
        try:
            await update.message.delete()
        except: pass

        keywords_part = text.replace("اضافه منشور", "").replace("أضف منشور", "").strip()

        if 'pending_keyword' in context.user_data:
            await send_admin_message(context, user.id, "❌ أكمل اختيار المنشور أولاً أو اكتب 'إلغاء' للبدء من جديد")
            return

        keyword = keywords_part.strip() if keywords_part else None

        news_list = await get_all_news()
        if not news_list:
            await send_admin_message(context, user.id, "❌ لا توجد منشورات متاحة")
            return

        if keyword:
            context.user_data['pending_keyword'] = keyword

        news_text = "📰 **اختر المنشور بالرد على هذه الرسالة بالرقم:**\n\n"
        for n in news_list[:10]:
            status = "✅" if n.is_published else "📝"
            news_text += f"{status} `{n.id}` - {n.content[:40]}\n"

        if len(news_list) > 10:
            news_text += f"\n... و {len(news_list) - 10} منشور آخر"

        if keyword:
            news_text += f"\n\n🔑 الكلمة المفتاحية: {keyword}"

        news_text += "\n\n💡 أرسل رقم المنشور المطلوب"

        await send_admin_message(context, user.id, news_text)
        return

    elif text.startswith("احذف منشور") or text.startswith("احذف المنشور"):
        try:
            await update.message.delete()
        except: pass
        id_part = text.replace("احذف منشور", "").replace("احذف المنشور", "").strip()
        
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب كتابة رقم المنشور\n\nمثال: احذف منشور 5")
            return

        try:
            news_id = int(id_part)
            await delete_news(news_id)
            await send_admin_message(context, user.id, f"✅ تمت حذف المنشور رقم {news_id}")
            await log_activity("delete_news", f"ID: {news_id}", user.id)
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل حذف المنشور: {str(e)}")

    elif text in ["قائمة المنشورات", "المنشورات", "عرض المنشورات", "جميع المنشورات", "قائمة المنشورات", "المنشورات", "عرض المنشورات"]:
        news = await get_all_news()
        if not news:
            await send_admin_message(context, user.id, "📭 لا توجد منشورات")
            return

        text_msg = "📰 **المنشورات:**\n\n"
        for n in news[:15]:
            status = "✅" if n.is_published else "📝"
            text_msg += f"{status} `{n.id}` - {n.content[:30]}\n"

        if len(news) > 15:
            text_msg += f"\n... و {len(news) - 15} منشور آخر"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    # ==================== إدارة المستخدمين ====================
    elif text.startswith("حظر"):
        try:
            await update.message.delete()
        except: pass

        # Via reply
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            target_id = update.message.reply_to_message.from_user.id
            parts = text.replace("حظر", "").strip().split(None, 1)
            reason = parts[0] if parts else "لا يوجد سبب"

            if await is_banned(target_id):
                await send_admin_message(context, user.id, "⚠️ هذا المستخدم محظور بالفعل.")
                return

            await ban_user(target_id, reason, user.id)
            await send_admin_message(context, user.id, f"🚫 تم حظر المستخدم `{target_id}`\n📋 السبب: {reason}")
            await log_activity("ban_user", f"User: {target_id}, Reason: {reason}", user.id)
            return

        # Via ID
        id_part = text.replace("حظر", "").strip()
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب التأشير على المستخدم أو كتابة رقمID\n\nمثال: رد على رسالة المستخدم بكلمة حظر")
            return

        parts = id_part.split(None, 1)
        try:
            target_id = int(parts[0])
            reason = parts[1] if len(parts) > 1 else "لا يوجد سبب"

            if await is_banned(target_id):
                await send_admin_message(context, user.id, "⚠️ هذا المستخدم محظور بالفعل.")
                return

            await ban_user(target_id, reason, user.id)
            await send_admin_message(context, user.id, f"🚫 تم حظر المستخدم `{target_id}`\n📋 السبب: {reason}")
            await log_activity("ban_user", f"User: {target_id}, Reason: {reason}", user.id)
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل الحظر: {str(e)}")

    elif text.startswith("الغاء حظر") or text.startswith("إلغاء حظر"):
        try:
            await update.message.delete()
        except: pass

        # Via reply
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            target_id = update.message.reply_to_message.from_user.id

            from sqlalchemy import delete as sql_delete
            from bot.models.models import BannedUser

            async with async_session() as session:
                await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == target_id))
                await session.commit()

            groups = await get_active_channel_groups()
            for group in groups:
                try:
                    await context.bot.unban_chat_member(chat_id=group.chat_id, user_id=target_id)
                except Exception:
                    pass

            await send_admin_message(context, user.id, f"✅ تم رفع الحظر عن المستخدم `{target_id}`")
            await log_activity("unban_user", f"User: {target_id}", user.id)
            return

        # Via ID
        id_part = text.replace("الغاء حظر", "").replace("إلغاء حظر", "").strip()
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب التأشير على المستخدم أو كتابة رقمID\n\nمثال: رد على رسالة المستخدم بكلمة الغاء حظر")
            return

        try:
            target_id = int(id_part)

            from sqlalchemy import delete as sql_delete
            from bot.models.models import BannedUser

            async with async_session() as session:
                await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == target_id))
                await session.commit()

            groups = await get_active_channel_groups()
            for group in groups:
                try:
                    await context.bot.unban_chat_member(chat_id=group.chat_id, user_id=target_id)
                except Exception:
                    pass

            await send_admin_message(context, user.id, f"✅ تم رفع الحظر عن المستخدم `{target_id}`")
            await log_activity("unban_user", f"User: {target_id}", user.id)
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل رفع الحظر: {str(e)}")

    elif text in ["قائمة المحظورين", "المحظورين", "عرض المحظورين"]:
        banned = await get_all_banned()
        if not banned:
            await send_admin_message(context, user.id, "✅ لا يوجد محظورين")
            return

        text_msg = "🚫 **قائمة المحظورين:**\n\n"
        for b in banned[:20]:
            text_msg += f"`{b.telegram_id}` - {b.reason or 'لا يوجد سبب'}\n"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    # ==================== عام ====================
    elif text in ["الاحصائيات", "احصائيات", "الإحصائيات", "إحصائيات", "stats"]:
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

        text_msg = f"""📊 **إحصائيات البوت:**

👥 المستخدمين: {total_users}
👥 القروبات: {total_groups}
❓ الاسئلة: {total_questions}
📰 المنشورات: {total_news}"""

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    elif text in ["القروبات", "قروبات", "عرض القروبات", "groups"]:
        groups = await get_active_channel_groups()
        if not groups:
            await send_admin_message(context, user.id, "📭 لا توجد قروبات مسجلة")
            return

        text_msg = "👥 **القروبات:**\n\n"
        for g in groups[:20]:
            status = "✅" if g.is_active else "❌"
            text_msg += f"{status} `{g.chat_id}` - {g.title or 'بدون عنوان'}\n"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    elif text.startswith("اذاعة") or text.startswith("إذاعة") or text.startswith("broadcast"):
        message = text.replace("اذاعة", "").replace("إذاعة", "").replace("broadcast", "").strip()
        
        if not message:
            await send_admin_message(context, user.id, "❌ يجب كتابة الرسالة\n\nمثال: اذاعة مرحبا بالجميع")
            return

        groups = await get_active_channel_groups()
        if not groups:
            await send_admin_message(context, user.id, "📭 لا توجد قروبات لإرسال الرسالة")
            return

        sent = 0
        failed = 0

        for group in groups:
            try:
                await context.bot.send_message(chat_id=group.chat_id, text=wrap_links_in_blockquote(message), disable_web_page_preview=True)
                sent += 1
            except Exception:
                failed += 1

        await send_admin_message(context, user.id, f"✅ تم الإرسال\n📤 نجح: {sent}\n❌ فشل: {failed}")
        await log_activity("broadcast", f"Sent: {sent}, Failed: {failed}", user.id)

    elif text in ["مساعدة", "المساعدة", "اوامر", "الأوامر", "help", "أوامر الادمن", "اوامر الادمن"]:
        help_text = """⚙️ **اوامر الادمن النصية**

**📋 الردود التلقائية:**
اضافه رد [كلمة] [رقم المنشور] - إضافة رد جديد
احذف رد [رقم] - حذف رد
قائمة الردود - عرض جميع الردود
بحث في الردود [كلمة] - البحث في الردود

**❓ الاسئلة الشائعة:**
اضافه سؤال [سؤال] [كلمات] [رقم المنشور] - إضافة سؤال
احذف سؤال [رقم] - حذف سؤال
قائمة الاسئلة - عرض الاسئلة
بحث في الاسئلة [كلمة] - البحث في الاسئلة

**📰 المنشورات:**
اضافه منشور - إضافة منشور
احذف منشور [رقم] - حذف منشور
قائمة المنشورات - عرض المنشورات

**👤 إدارة المستخدمين:**
حظر [رقم] [سبب] - حظر مستخدم
الغاء حظر [رقم] - رفع الحظر
قائمة المحظورين - قائمة المحظورين

**📊 عام:**
الاحصائيات - إحصائيات البوت
القروبات - قائمة القروبات
اذاعة [رسالة] - إرسال للجميع
مساعدة - عرض هذه الرسالة"""

        await send_admin_message(context, user.id, help_text, parse_mode=ParseMode.MARKDOWN)


# ==================== اوامر الرد على الرسائل ====================

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.reply_to_message:
        return

    text = update.message.text.strip()
    user = update.effective_user
    chat = update.effective_chat

    is_chat_admin = False
    try:
        member = await chat.get_member(user.id)
        is_chat_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        pass

    is_bot_admin = user.id in context.bot_data.get('admin_ids', [])

    if not is_chat_admin and not is_bot_admin:
        return

    target_user = update.message.reply_to_message.from_user
    target_user_id = target_user.id

    if text.startswith("اضافه منشور") or text.startswith("أضف منشور") or text.startswith("اضافة منشور"):
        try:
            await update.message.delete()
        except: pass

        keywords_part = text.replace("اضافه منشور", "").replace("أضف منشور", "").replace("اضافة منشور", "").strip()
        replied = update.message.reply_to_message

        content = replied.text or replied.caption or ""

        if not content and not (replied.photo or replied.video or replied.document or replied.voice or replied.audio):
            await send_admin_message(context, user.id, "❌ الرسالة المُشار إليها لا تحتوي على محتوى")
            return

        file_url = None
        file_type = None
        file_tg_id = None
        thumbnail_url = None
        file_name = None

        try:
            if replied.photo:
                file_obj = replied.photo[-1]
                file_type = "photo"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_image(bytes(file_bytes), folder="kku-bot/news")
            elif replied.video:
                file_obj = replied.video
                file_type = "video"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_file(bytes(file_bytes), folder="kku-bot/news")
            elif replied.document:
                file_obj = replied.document
                file_type = "document"
                file_tg_id = file_obj.file_id
                file_name = file_obj.file_name
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_raw(bytes(file_bytes), filename=file_name or "file", folder="kku-bot/news")
            elif replied.voice or replied.audio:
                file_obj = replied.voice or replied.audio
                file_type = "document"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_raw(bytes(file_bytes), filename="audio", folder="kku-bot/news")
        except Exception as e:
            logger.warning(f"Could not upload file from replied message: {e}")

        try:
            import json
            target_channels = json.dumps([str(chat.id)])

            files_json_data = []
            if file_url:
                files_json_data.append({
                    "url": file_url,
                    "type": file_type or "document",
                    "name": file_name or "file",
                    "thumbnail": thumbnail_url,
                })

            news = await add_news(
                content=content,
                image_url=file_url if file_type == "photo" else None,
                file_url=file_url if file_type != "photo" else None,
                thumbnail_url=thumbnail_url,
                file_name=file_name,
                file_type=file_type,
                created_by=user.id,
                file_id=file_tg_id,
                as_document=(file_type == "document"),
                target_channels=target_channels,
                files_json=json.dumps(files_json_data) if files_json_data else None
            )

            if keywords_part:
                keyword = keywords_part.strip()
                await add_auto_response(
                    keyword=keyword,
                    response="تم الرد عبر المنشور",
                    created_by=user.id,
                    news_id=news.id,
                    file_url=file_url,
                    file_type=file_type
                )
                await send_admin_message(context, user.id, f"✅ تمت إضافة المنشور\n\n🔑 الكلمة: {keyword}\n📰 المنشور: {news.id}")
            else:
                await send_admin_message(context, user.id, f"✅ تمت إضافة المنشور رقم {news.id}")

            await log_activity("add_news", f"ID: {news.id}, Keyword: {keywords_part}", user.id)
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل إضافة المنشور: {str(e)}")
        return

    try:
        target_member = await chat.get_member(target_user_id)
        if target_member.status in [ChatMemberStatus.OWNER]:
            if user.id not in ADMIN_IDS:
                await send_admin_message(context, user.id, "❌ لا يمكنك تنفيذ هذا الأمر على مالك القروب")
                return
    except:
        pass

    if text in ["حذف", "حذفا", "ازالة", "ازل", "زل", "امسح", "مسح"]:
        try:
            await update.message.delete()
        except: pass
        try:
            await update.message.reply_to_message.delete()
            await send_admin_message(context, user.id, f"✅ تم حذف رسالة {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في حذف الرسالة: {e}")

    elif text in ["حظر", "احظر", "ban"]:
        try:
            await update.message.delete()
        except: pass
        try:
            await chat.ban_member(target_user_id)
            await send_admin_message(context, user.id, f"🚫 تم حظر {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في حظر المستخدم: {e}")

    elif text in ["الغاء حظر", "الغاء الحظر", "الغي حظر", "شيل حظر", "شيل الحظر", "الغي الحظر", "unban"]:
        try:
            await update.message.delete()
        except: pass
        try:
            async with async_session() as session:
                await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == target_user_id))
                await session.commit()

            groups = await get_active_channel_groups()
            unbanned_count = 0
            for group in groups:
                try:
                    await context.bot.unban_chat_member(chat_id=group.chat_id, user_id=target_user_id)
                    unbanned_count += 1
                except Exception:
                    pass

            if unbanned_count > 0:
                await send_admin_message(context, user.id, f"✅ تم رفع الحظر عن {target_user.first_name} من {unbanned_count} قروب")
            else:
                await send_admin_message(context, user.id, f"✅ تم رفع الحظر عن {target_user.first_name}")
            await log_activity("unban_user", f"User: {target_user_id}", user.id)
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في إلغاء الحظر: {e}")

    elif text in ["طرد", "اطرد", "kick"]:
        try:
            await update.message.delete()
        except: pass
        try:
            await chat.ban_member(target_user_id)
            await chat.unban_member(target_user_id)
            await send_admin_message(context, user.id, f"👢 تم طرد {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في طرد المستخدم: {e}")

    elif text in ["تثبيت", "ثبت", "pin"]:
        try:
            await update.message.reply_to_message.pin()
            await send_admin_message(context, user.id, f"📌 تم تثبيت رسالة {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في تثبيت الرسالة: {e}")

    elif text in ["الغاء تثبيت", "الغي تثبيت", "unpin"]:
        try:
            await update.message.reply_to_message.unpin()
            await send_admin_message(context, user.id, f"📌 تم الغاء تثبيت رسالة {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في الغاء تثبيت الرسالة: {e}")

    elif text.startswith("اضافه رد") or text.startswith("أضف رد") or text.startswith("اضف رد") or text.startswith("ضف رد"):
        keywords_part = text.replace("اضافه رد", "").replace("أضف رد", "").replace("اضف رد", "").replace("ضف رد", "").strip()
        replied = update.message.reply_to_message
        
        if not replied:
            await send_admin_message(context, user.id,
                "❌ الطريقة الصحيحة:\n"
                "1. رد على رسالة في الجروب\n"
                "2. اكتب:\nاضافه رد [كلمات مفتاحية بفواصل]\n\n"
                "💡 مثال:\n"
                "اضافه رد تسجيل,القبول")
            return
        
        response_text = replied.text or replied.caption or ""
        
        if not response_text and not (replied.photo or replied.video or replied.document or replied.voice or replied.audio):
            await send_admin_message(context, user.id, "❌ يجب أن تحتوي الرسالة المُشار إليها على نص أو مرفق")
            return

        if not keywords_part:
            await send_admin_message(context, user.id,
                "❌ يجب كتابة الكلمات المفتاحية\n\n"
                "💡 الصيغة:\n"
                "اضافه رد تسجيل,القبول")
            return

        # Split keywords by comma
        keywords = [k.strip() for k in keywords_part.replace("،", ",").split(",") if k.strip()]
        
        if not keywords:
            await send_admin_message(context, user.id, "❌ يجب كتابة كلمة مفتاحية واحدة على الأقل")
            return

        # Get file from replied message
        file_url = None
        file_type = None
        file_tg_id = None
        
        try:
            if replied.photo:
                file_obj = replied.photo[-1]
                file_type = "photo"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_image(bytes(file_bytes), folder="kku-bot/responses")
            elif replied.video:
                file_obj = replied.video
                file_type = "video"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_file(bytes(file_bytes), folder="kku-bot/responses")
            elif replied.document:
                file_obj = replied.document
                file_type = "document"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_raw(bytes(file_bytes), filename=file_obj.file_name or "file", folder="kku-bot/responses")
            elif replied.voice or replied.audio:
                file_obj = replied.voice or replied.audio
                file_type = "document"
                file_tg_id = file_obj.file_id
                tg_file = await file_obj.get_file()
                file_bytes = await tg_file.download_as_bytearray()
                file_url = upload_raw(bytes(file_bytes), filename="audio", folder="kku-bot/responses")
        except Exception as e:
            logger.warning(f"Could not upload file from replied message: {e}")

        # Create auto-responses
        created_count = 0
        for keyword in keywords:
            try:
                ar = AutoResponse(
                    keyword=keyword,
                    response=response_text,
                    created_by=user.id,
                    file_url=file_url,
                    file_type=file_type,
                    file_tg_id=file_tg_id,
                    source_chat_id=chat.id,
                    source_message_id=replied.message_id,
                )
                async with async_session() as session:
                    session.add(ar)
                    await session.commit()
                created_count += 1
            except Exception as e:
                logger.error(f"Could not create auto response for keyword '{keyword}': {e}")

        if created_count > 0:
            file_info = f"\n📎 مرفق: {file_type}" if file_type else ""
            await send_admin_message(context, user.id, f"✅ تم إضافة {created_count} رد تلقائي:\n{', '.join(keywords)}{file_info}")
        else:
            await send_admin_message(context, user.id, "❌ فشل في إنشاء الردود التلقائية")
        return

    elif text.strip() in ["ازاله الرد", "ازالة الرد", "ازل رد"]:
        try:
            await update.message.delete()
        except: pass
        replied = update.message.reply_to_message
        responses = await get_auto_responses_by_source(chat.id, replied.message_id)
        if not responses:
            await send_admin_message(context, user.id, "❌ لا توجد ردود تلقائية مرتبطة بهذه الرسالة")
            return

        keywords = [r.keyword for r in responses]
        await remove_auto_responses_by_source(chat.id, replied.message_id)
        await send_admin_message(context, user.id, f"✅ تم إزالة {len(responses)} رد تلقائي:\n{', '.join(keywords)}")


# ==================== تسجيل الاوامر ====================

admin_text = MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.REPLY, admin_text_handler)
admin_reply = MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.GROUPS, admin_reply_handler)
