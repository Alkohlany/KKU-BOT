from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from bot.services.database import get_auto_responses, get_all_auto_responses, search_question, increment_question_usage
from bot.middleware.subscription import check_subscription
from bot.services.responses_system import DEFAULT_RESPONSES
from bot.config import CHANNEL_LINK
import logging
import unicodedata
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def normalize_arabic(text):
    """تطبيع النص العربي"""
    text = unicodedata.normalize('NFKD', text)
    text = text.replace('ً', '').replace('ٌ', '').replace('ٍ', '')
    text = text.replace('َ', '').replace('ُ', '').replace('ِ', '').replace('ّ', '').replace('ْ', '')
    text = text.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('إ', 'ا').replace('أ', 'ا').replace('آ', 'ا')
    return text


def fuzzy_match(text, keyword, threshold=0.7):
    """تطابق ضبابي"""
    return SequenceMatcher(None, text, keyword).ratio() >= threshold


def find_best_match(text, responses):
    """أفضل تطابق"""
    normalized = normalize_arabic(text.lower().strip())

    for response in responses:
        if response.keyword.lower().strip() == normalized:
            return response

    for response in responses:
        keyword = response.keyword.lower().strip()
        if keyword in normalized or normalized in keyword:
            return response

    best_match = None
    best_score = 0
    for response in responses:
        score = fuzzy_match(normalized, response.keyword.lower())
        if score > best_score and score >= 0.5:
            best_score = score
            best_match = response

    return best_match


def find_best_question(text, questions):
    """أفضل تطابق سؤال"""
    normalized = normalize_arabic(text.lower().strip())
    
    for q in questions:
        if q.question.lower().strip() == normalized:
            return q
    
    for q in questions:
        q_words = set(q.question.lower().split())
        t_words = set(normalized.split())
        common = q_words & t_words
        if len(common) >= 2:
            return q
    
    best_match = None
    best_score = 0
    for q in questions:
        score = SequenceMatcher(None, normalized, q.question.lower()).ratio()
        if score > best_score and score >= 0.5:
            best_score = score
            best_match = q
    
    return best_match


async def handle_auto_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الردود التلقائية بشكل ذكي"""
    if not update.message or not update.message.text:
        return
    
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        user = update.effective_user
        if user:
            is_subscribed = await check_subscription(user.id, context)
            if not is_subscribed:
                await update.message.delete()
                await update.message.reply_text(
                    f"يا {user.first_name} عليك الاشتراك في القناة الرسمية أولاً"
                )
                return
    
    text = update.message.text.strip()
    
    if not text or len(text) < 2:
        return
    
    if len(text) > 200:
        return
    
    plan_triggers = ["خطة", "خطط", "خطه"]
    if any(word in text for word in plan_triggers):
        return
    
    custom_responses = await get_all_auto_responses()
    if custom_responses:
        best_match = find_best_match(text, custom_responses)
        if best_match:
            await update.message.reply_text(best_match.response)
            return
    
    normalized_text = normalize_arabic(text.lower().strip())
    for keyword, response in DEFAULT_RESPONSES.items():
        if keyword.lower() in normalized_text or normalized_text in keyword.lower():
            await update.message.reply_text(response)
            return
    
    questions = await search_question(text)
    if questions:
        if isinstance(questions, list):
            question_result = questions[0] if questions else None
        else:
            question_result = questions
        
        if question_result:
            await increment_question_usage(question_result.id)
            await update.message.reply_text(
                f"❓ {question_result.question}\n\n✅ {question_result.answer}"
            )


auto_response_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auto_response)
