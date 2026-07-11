from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from bot.middleware.subscription import subscription_required
from bot.services.database import get_user, create_user
import logging

logger = logging.getLogger(__name__)

START_MESSAGE = """اهلا بك في بوت ادارة وحماية قروبات جامعة الملك خالد 🤍

✅ البوت المعتمد لقروبات الجامعة 

اذا عندك اي قروب خاص بجامعة الملك خالد
اضف البوت ادمن للقروب وبيتفعل عطول جمعنا فيه كل الردود الخاصه بجامعة الملك خالد 

نفس السنه الي راحت في اضافات وتحديث جديد في البوت المعتمد لقروبات الجامعة

🟢 مميزات البوت الجديدة 
١- تم اضافة كل الردود الخاصه بالجامعة 
٢- تم تضمين كل الاجوبه على أسئلة الطلاب 
٣- تم اضافة خاصية المنشورات المهمه المتعلقة بالجامعة(اي خبر مهم بينزل في كل القروبات الي فيها البوت ادمن)
٤- واهم شي خاصية التعرف على الحسابات المزعجة ( اذا في حساب مزعج او حساب اعلانات بيتم ازالة الحساب من كل القروبات)

اختر الميزة التي تريدها:"""

FEATURES_KEYBOARD = [
    [InlineKeyboardButton("📰 المنشورات", callback_data="feature_news")],
    [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="feature_questions")],
    [InlineKeyboardButton("📋 الخطط الدراسية", callback_data="feature_plans")],
    [InlineKeyboardButton("💬 الردود", callback_data="feature_responses")],
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    db_user = await get_user(user.id)
    if not db_user:
        db_user = await create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    if context.args and context.args[0] == "plans":
        from bot.handlers.study_plans import plans_command
        await plans_command(update, context)
        return

    markup = InlineKeyboardMarkup(FEATURES_KEYBOARD)
    await update.message.reply_text(START_MESSAGE, reply_markup=markup, disable_web_page_preview=True)


async def feature_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    feature = query.data.replace("feature_", "")
    
    if feature == "news":
        from bot.handlers.news import get_news_text
        text = await get_news_text()
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    elif feature == "questions":
        from bot.handlers.questions import get_questions_text
        text = await get_questions_text()
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    elif feature == "plans":
        from bot.handlers.study_plans import get_plans_text
        text = await get_plans_text()
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    elif feature == "responses":
        from bot.handlers.responses import get_responses_text
        text = await get_responses_text()
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)


start_handler = CommandHandler("start", start_command)
feature_handler = CallbackQueryHandler(feature_callback, pattern="^feature_")
