from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.middleware.subscription import subscription_required
from bot.services.database import search_question, get_all_questions
import logging

logger = logging.getLogger(__name__)


async def get_questions_text():
    questions = await get_all_questions()
    if not questions:
        return "لا توجد أسئلة مسجلة حالياً 📭"
    
    text = "📚 الأسئلة الشائعة:\n\n"
    for q in questions[:10]:
        text += f"• {q.question}\n"
    text += "\n💡 اكتب سؤالك بعد الأمر مثل:\n/questions كيف أسجل مواد"
    return text


async def questions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return
    
    if context.args:
        query = " ".join(context.args)
        result = await search_question(query)
        if result:
            if result.file_url:
                if result.file_type == 'photo':
                    await update.message.reply_photo(photo=result.file_url, caption=f"❓ {result.question}\n\n✅ {result.answer}")
                elif result.file_type == 'video':
                    await update.message.reply_video(video=result.file_url, caption=f"❓ {result.question}\n\n✅ {result.answer}")
                else:
                    await update.message.reply_document(document=result.file_url, caption=f"❓ {result.question}\n\n✅ {result.answer}")
            else:
                await update.message.reply_text(f"❓ {result.question}\n\n✅ {result.answer}")
        else:
            await update.message.reply_text("لم أجد جواب على سؤالك، جرب أسئلة ثانية أو اسأل في القروب")
    else:
        questions = await get_all_questions()
        if not questions:
            await update.message.reply_text("لا توجد أسئلة مسجلة حالياً 📭")
            return
        
        text = "📚 الأسئلة الشائعة:\n\n"
        for q in questions[:10]:
            text += f"• {q.question}\n"
        text += "\n💡 اكتب سؤالك بعد الأمر مثل:\n/questions كيف أسجل مواد"
        await update.message.reply_text(text)


questions_handler = CommandHandler("questions", questions_command)
