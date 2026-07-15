from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from bot.middleware.subscription import subscription_required
from bot.services.database import get_all_study_plan_groups, get_active_channel_groups, get_official_channel
from bot.services.news_publisher import wrap_links_in_blockquote
import logging

logger = logging.getLogger(__name__)


async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type in ['group', 'supergroup']:
        bot_username = context.bot.username
        await update.message.reply_text(
            f"🟢 هنا خطط التخصصات جامعة الملك خالد \n\n"
            f"https://t.me/{bot_username}?start=plans", disable_web_page_preview=True)
        return

    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    text = await get_plans_text()
    await update.message.reply_text(wrap_links_in_blockquote(text), parse_mode='HTML', disable_web_page_preview=True)


async def get_plans_text() -> str:
    groups = await get_all_study_plan_groups()
    groups = [g for g in groups if g.channel_message_id is not None]

    if not groups:
        return "لا توجد خطط دراسية منشورة حالياً 📭"

    channel = await get_official_channel()
    if not channel:
        all_channels = await get_active_channel_groups()
        for ch in all_channels:
            if ch.type == 'channel':
                channel = ch
                break
    if not channel:
        return "لا توجد قناة نشرة حالياً 📭"

    channel_username = None
    if channel.invite_link and 't.me/' in channel.invite_link:
        channel_username = channel.invite_link.split('t.me/')[-1].strip('/')
    if not channel_username:
        channel_username = str(channel.chat_id)

    text = "📚 محدث خطط التخصصات\n"
    text += "جامعة الملك خالد 1447هـ\n\n"

    for group in groups:
        group_link = f"https://t.me/{channel_username}/{group.channel_message_id}"
        text += f"{group.title} 🔻\n{group_link}\n\n"

    text += "🔴 انضموا لقروب جامعة الملك خالد العام 🔻\n"
    text += "https://t.me/KKU_Main1\n\n"
    text += "🟠 انضموا لقروب الواتساب العام 🔻\n"
    text += "https://whatsapp.com/channel/0029VbD8NhHC1FuKSEmrJY2W\n\n"
    text += "#شاركها_فربما_يبحث_عنها_غيرك"

    return text


async def plans_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    for trigger in ["الخطط", "الخطة", "الخطه", "خطط", "خطة", "خطه"]:
        if text.startswith(trigger):
            remaining = text[len(trigger):].strip()
            break
    else:
        remaining = text
    context.args = remaining.split() if remaining else []
    await plans_command(update, context)


plans_handler = CommandHandler("plans", plans_command)
plans_text_handler = MessageHandler(filters.Regex("^(خطة|خطط|خطه|الخطة|الخطط|الخطه)"), plans_text_command)
