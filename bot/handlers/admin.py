from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.constants import ChatMemberStatus, ParseMode
from bot.config import ADMIN_IDS
from bot.services.cloud_storage import upload_raw
from bot.services.database import (
    get_auto_responses_by_source, remove_auto_responses_by_source,
    add_auto_response, get_all_auto_responses, remove_auto_response,
    add_question, get_all_questions, delete_question,
    get_all_news, delete_news,
    ban_user, get_all_banned, is_banned,
    get_all_groups, log_activity, async_session
)
import cloudinary.uploader
import logging
from bot.models.models import AutoResponse

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
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
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
        keywords_part = text.replace("اضافه رد", "").replace("أضف رد", "").replace("اضف رد", "").strip()
        
        if not keywords_part:
            await send_admin_message(context, user.id,
                "❌ الطريقة الصحيحة:\n"
                "اضافه رد [كلمة] [رقم المنشور]\n\n"
                "💡 يمكنك أيضاً الرد على رسالة وإرسال:\n"
                "اضافه رد [كلمة]",
            )
            return

        parts = keywords_part.split(None, 1)
        if len(parts) < 2:
            await send_admin_message(context, user.id, "❌ يجب كتابة الكلمة ورقم المنشور\n\nمثال: اضافه رد تسجيل 5")
            return

        keyword = parts[0]
        try:
            news_id = int(parts[1])
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح لرقم المنشور")
            return

        try:
            await add_auto_response(
                keyword=keyword,
                response="تم الرد عبر المنشور",
                created_by=user.id,
                news_id=news_id
            )
            await send_admin_message(context, user.id, f"✅ تمت إضافة الرد\n\n🔑 الكلمة: {keyword}\n📰 المنشور: {news_id}")
            await log_activity("add_response", f"Keyword: {keyword}, News: {news_id}", user.id)
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل إضافة الرد: {str(e)}")

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
        await send_admin_message(context, user.id,
            "📰 لإضافة منشور:\n"
            "1. ارسل العنوان كرسالة\n"
            "2. رد عليها بالمحتوى\n"
            "3. ارفق الصورة أو الملف اختيارياً\n"
            "4. اكتب:\nاضافه منشور\n\n"
            "💡 يمكنك أيضاً استخدام الداشبورد من الويب"
        )

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
            text_msg += f"{status} `{n.id}` - {n.title[:30]}\n"

        if len(news) > 15:
            text_msg += f"\n... و {len(news) - 15} منشور آخر"

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    # ==================== إدارة المستخدمين ====================
    elif text.startswith("حظر"):
        try:
            await update.message.delete()
        except: pass
        id_part = text.replace("حظر", "").strip()
        
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب كتابة رقم المستخدم\n\nمثال: حظر 12345678 سبب الحظر")
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
        id_part = text.replace("الغاء حظر", "").replace("إلغاء حظر", "").strip()
        
        if not id_part:
            await send_admin_message(context, user.id, "❌ يجب كتابة رقم المستخدم\n\nمثال: الغاء حظر 12345678")
            return

        try:
            target_id = int(id_part)
            
            from sqlalchemy import delete as sql_delete
            from bot.models.models import BannedUser

            async with async_session() as session:
                await session.execute(sql_delete(BannedUser).where(BannedUser.telegram_id == target_id))
                await session.commit()

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

        text_msg = f"""📊 **إحصائيات البوت:**

👥 المستخدمين: {total_users}
👥 القروبات: {total_groups}
❓ الاسئلة: {total_questions}
📰 المنشورات: {total_news}"""

        await send_admin_message(context, user.id, text_msg, parse_mode=ParseMode.MARKDOWN)

    elif text in ["القروبات", "قروبات", "عرض القروبات", "groups"]:
        groups = await get_all_groups()
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

        groups = await get_all_groups()
        if not groups:
            await send_admin_message(context, user.id, "📭 لا توجد قروبات لإرسال الرسالة")
            return

        sent = 0
        failed = 0

        for group in groups:
            try:
                await context.bot.send_message(chat_id=group.chat_id, text=message)
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

    try:
        target_member = await chat.get_member(target_user_id)
        if target_member.status in [ChatMemberStatus.OWNER]:
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
            await update.message.reply_to_message.delete()
            await send_admin_message(context, user.id, f"🚫 تم حظر {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في حظر المستخدم: {e}")

    elif text in ["الغاء حظر", "الغي حظر", "unban"]:
        try:
            await update.message.delete()
        except: pass
        try:
            await chat.unban_member(target_user_id)
            await send_admin_message(context, user.id, f"✅ تم إلغاء حظر {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في إلغاء الحظر: {e}")

    elif text in ["طرد", "اطرد", "kick"]:
        try:
            await update.message.delete()
        except: pass
        try:
            await chat.ban_member(target_user_id)
            await chat.unban_member(target_user_id)
            await update.message.reply_to_message.delete()
            await send_admin_message(context, user.id, f"👢 تم طرد {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في طرد المستخدم: {e}")

    elif text in ["تثبيت", "ثبت", "pin"]:
        try:
            await update.message.reply_to_message.pin()
            await send_admin_message(context, user.id, f"📌 تم تثبيت رسالة {target_user.first_name}")
        except Exception as e:
            await send_admin_message(context, user.id, f"❌ فشل في تثبيت الرسالة: {e}")

    elif text.startswith("اضافه رد") or text.startswith("أضف رد") or text.startswith("اضف رد") or text.startswith("ضف رد"):
        try:
            await update.message.delete()
        except: pass
        
        keywords_part = text.replace("اضافه رد", "").replace("أضف رد", "").replace("اضف رد", "").replace("ضف رد", "").strip()
        
        if not keywords_part:
            await send_admin_message(context, user.id,
                "❌ الطريقة الصحيحة:\n"
                "اضافه رد [كلمات مفتاحية بفواصل] [رقم المنشور]\n\n"
                "💡 مثال:\n"
                "اضافه رد تسجيل,القبول 5\n\n"
                "💡 يمكنك أيضاً الرد على رسالة تحتوي على المنشور")
            return
        
        # Parse keywords and news_id
        parts = keywords_part.rsplit(None, 1)
        if len(parts) < 2:
            await send_admin_message(context, user.id, "❌ يجب كتابة الكلمات ورقم المنشور\n\nمثال: اضافه رد تسجيل,القبول 5")
            return
        
        keywords_text = parts[0]
        try:
            news_id = int(parts[1])
        except ValueError:
            await send_admin_message(context, user.id, "❌ يجب إدخال رقم صحيح لرقم المنشور")
            return
        
        # Split keywords by comma
        keywords = [k.strip() for k in keywords_text.replace("،", ",").split(",") if k.strip()]
        
        if not keywords:
            await send_admin_message(context, user.id, "❌ يجب كتابة كلمة مفتاحية واحدة على الأقل")
            return
        
        # Create auto-responses with news_id
        created_count = 0
        for keyword in keywords:
            try:
                await add_auto_response(
                    keyword=keyword,
                    response="تم الرد عبر المنشور",
                    created_by=user.id,
                    news_id=news_id
                )
                created_count += 1
            except Exception as e:
                logger.error(f"Could not create auto response for keyword '{keyword}': {e}")
        
        if created_count > 0:
            await send_admin_message(context, user.id, f"✅ تم إضافة {created_count} رد تلقائي:\n{', '.join(keywords)}\n📰 المنشور: {news_id}")
        else:
            await send_admin_message(context, user.id, "❌ فشل في إنشاء الردود التلقائية")

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
