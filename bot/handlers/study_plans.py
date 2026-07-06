from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.middleware.subscription import subscription_required
from bot.services.database import (
    get_all_study_plans, get_study_plan_by_id, search_study_plans,
    get_all_study_plan_groups, get_study_plan_group_by_id
)
from bot.config import CHANNEL_ID
import logging

logger = logging.getLogger(__name__)


async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type in ['group', 'supergroup']:
        bot_username = context.bot.username
        await update.message.reply_text(
            f"📚 للاطلاع على الخطط الدراسية يرجى استخدام البوت في المحادثة الخاصة:\n"
            f"https://t.me/{bot_username}?start=plans"
        )
        return

    is_subscribed = await subscription_required(update, context)
    if not is_subscribed:
        return

    groups = await get_all_study_plan_groups()
    if not groups:
        await update.message.reply_text("لا توجد مجموعات خطط دراسية مسجلة حالياً 📭")
        return

    keyboard = []
    for group in groups:
        keyboard.append([InlineKeyboardButton(group.title, callback_data=f"plan_group_{group.id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📋 الخطط الدراسية:",
        reply_markup=reply_markup
    )


async def plan_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    group_id = int(query.data.split("_")[2])
    group = await get_study_plan_group_by_id(group_id)

    if not group:
        await query.answer("❌ المجموعة غير موجودة", show_alert=True)
        return

    if not group.channel_message_id:
        await query.answer("⚠️ هذه المجموعة لم تُنشر على القناة بعد", show_alert=True)
        return

    channel_username = CHANNEL_ID.replace("@", "")
    channel_link = f"https://t.me/{channel_username}/{group.channel_message_id}"

    await query.answer(url=channel_link)


async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = int(query.data.split("_")[1])
    plan = await get_study_plan_by_id(plan_id)

    if not plan:
        await query.edit_message_text("❌ الخطة غير موجودة")
        return

    if plan.channel_message_id:
        channel_username = CHANNEL_ID.replace("@", "")
        channel_link = f"https://t.me/{channel_username}/{plan.channel_message_id}"
        await query.answer(url=channel_link, show_alert=False)
    else:
        await query.answer("❌ الخطة غير منشئة على القناة بعد", show_alert=True)


async def plans_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.message.delete()
    except Exception:
        pass

    groups = await get_all_study_plan_groups()
    if groups:
        keyboard = []
        for group in groups:
            keyboard.append([InlineKeyboardButton(f"📁 {group.title}", callback_data=f"plan_group_{group.id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="📋 الخطط الدراسية:",
            reply_markup=reply_markup
        )
        return

    try:
        plans = await get_all_study_plans()
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="❌ حدث خطأ أثناء جلب الخطط"
        )
        return

    if not plans:
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="لا توجد خطط دراسية مسجلة حالياً 📭"
        )
        return

    keyboard = []
    for plan in plans:
        keyboard.append([InlineKeyboardButton(plan.title, callback_data=f"plan_{plan.id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text="📋 اختر الخطة الدراسية:",
        reply_markup=reply_markup
    )


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
plan_group_callback_handler = CallbackQueryHandler(plan_group_callback, pattern="^plan_group_")
plan_callback_handler = CallbackQueryHandler(plan_callback, pattern="^plan_")
plans_back_handler = CallbackQueryHandler(plans_back_callback, pattern="^plans_back$")
