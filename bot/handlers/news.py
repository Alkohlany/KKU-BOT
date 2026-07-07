from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.middleware.subscription import subscription_required
from bot.services.database import get_all_news
import logging

logger = logging.getLogger(__name__)


async def get_news_text():
    news_list = await get_all_news()
    if not news_list:
        return "لا توجد منشورات حالياً 📭"
    
    text = "📰 آخر المنشورات:\n\n"
    for news in news_list[:5]:
        text += f"📌 {news.title}\n{news.content}\n\n"
        if news.image_url:
            text += "🖼️ يحتوي على صورة\n\n"
        text += "─" * 20 + "\n\n"
    
    return text


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return
    
    news_list = await get_all_news()
    if not news_list:
        await update.message.reply_text("لا توجد منشورات حالياً 📭")
        return
    
    for news in news_list[:5]:
        text = f"📰 {news.title}\n\n{news.content}"
        if news.image_url:
            await update.message.reply_photo(photo=news.image_url, caption=text)
        elif news.file_url:
            if news.file_type == 'video':
                await update.message.reply_video(video=news.file_url, caption=text)
            else:
                await update.message.reply_document(document=news.file_url, caption=text)
        else:
            await update.message.reply_text(text)


news_handler = CommandHandler("news", news_command)
