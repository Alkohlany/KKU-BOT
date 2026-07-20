from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from bot.services.database import get_auto_responses, search_question, increment_question_usage, get_news_by_id, log_activity, get_setting
from bot.services.ai import search_university_info, _call_model
from bot.services.news_publisher import wrap_links_in_blockquote
from bot.config import normalize_arabic
import logging
import re
import asyncio
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

DEFAULT_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 🌙",
    "السلام": "وعليكم السلام ورحمة الله 🌙",
    "اهلا": "أهلاً وسهلاً بك 💚",
    "مرحبا": "مرحباً بك في جامعة الملك خالد 🎓",
    "صباح الخير": "صباح النور ☀️",
    "مساء الخير": "مساء النور 🌙",
    "شكرا": "العفو، نحن في الخدمة 💚",
    "يعطيك العافية": "وإياك، الله يعطيك العافية 🌸",
}


def find_best_match(text, responses):
    """أفضل تطابق"""
    normalized = normalize_arabic(text.lower().strip())

    for response in responses:
        keyword_normalized = normalize_arabic(response.keyword.lower().strip())
        if keyword_normalized == normalized:
            return response

    sorted_responses = sorted(responses, key=lambda r: len(r.keyword), reverse=True)
    for response in sorted_responses:
        keyword_normalized = normalize_arabic(response.keyword.lower().strip())
        if keyword_normalized in normalized or (len(normalized) >= 3 and normalized in keyword_normalized):
            return response

    for response in responses:
        keyword_normalized = normalize_arabic(response.keyword.lower().strip())
        kw_list = keyword_normalized.split()
        txt_words = set(normalized.split())
        # Check if 3+ consecutive keyword words appear in text
        for i in range(len(kw_list) - 2):
            if all(w in txt_words for w in kw_list[i:i+3]):
                return response
        # Also check set overlap both directions
        if kw_words := set(kw_list):
            overlap = len(kw_words & txt_words) / len(kw_words)
            reverse = len(kw_words & txt_words) / len(txt_words) if txt_words else 0
            if overlap >= 0.7 or reverse >= 0.5:
                return response

    best_match = None
    best_score = 0
    for response in responses:
        keyword_normalized = normalize_arabic(response.keyword.lower().strip())
        score = SequenceMatcher(None, normalized, keyword_normalized).ratio()
        if score > best_score and score >= 0.6:
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

    if update.effective_user and update.effective_user.id == context.bot.id:
        return
    
    text = update.message.text.strip()
    
    if not text or len(text) < 2:
        return

    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        bot_message = update.message.reply_to_message.text or ""
        if bot_message:
            bot_message = bot_message[:500]
            search_query = f"{text} جامعة الملك خالد"
            logger.info(f"CONVERSATIONAL: reply detected. bot_msg='{bot_message[:80]}...' user_reply='{text[:80]}...'")
            try:
                ai_fallback_enabled = await get_setting("ai_fallback_enabled")
                if ai_fallback_enabled == "false":
                    logger.info("CONVERSATIONAL: AI fallback disabled, skipping")
                    return
                search_reply = await asyncio.to_thread(search_university_info, search_query)
                if search_reply and search_reply.strip():
                    await update.message.reply_text(wrap_links_in_blockquote(search_reply.strip()), parse_mode='HTML', disable_web_page_preview=True)
                    await log_activity(
                        action="conversational_reply",
                        details=f"رد محادثة مع بحث على: {text[:50]}...",
                        performed_by=update.effective_user.id if update.effective_user else 0
                    )
                    logger.info("CONVERSATIONAL: reply sent successfully with search")
                    return
            except Exception as e:
                logger.warning(f"CONVERSATIONAL: search error: {e}")
        else:
            logger.info("CONVERSATIONAL: bot message had no text (media), skipping")

    if len(text) > 200:
        return
    
    plan_triggers = ["خطة", "خطط", "خطه"]
    if any(word in text for word in plan_triggers):
        return
    
    custom_responses = await get_auto_responses()
    logger.info(f"AUTO_RESPONSE: text='{text}' custom_count={len(custom_responses)}")
    if custom_responses:
        best_match = find_best_match(text, custom_responses)
        if best_match:
            logger.info(f"AUTO_RESPONSE: matched keyword='{best_match.keyword}' response_len={len(best_match.response or '')} file_tg_id={'yes' if best_match.file_tg_id else 'no'}")
            try:
                if best_match.news_id:
                    news_post = await get_news_by_id(best_match.news_id)
                    if news_post:
                        content = wrap_links_in_blockquote(news_post.content or "")
                        if news_post.image_url:
                            await update.message.reply_photo(photo=news_post.image_url, caption=content, parse_mode='HTML')
                        elif news_post.file_url:
                            await update.message.reply_document(document=news_post.file_url, caption=content, parse_mode='HTML')
                        else:
                            await update.message.reply_text(content, parse_mode='HTML', disable_web_page_preview=True)
                        logger.info("AUTO_RESPONSE: sent news post")
                        return
                if not best_match.response and not best_match.file_tg_id and not best_match.file_url:
                    logger.info("AUTO_RESPONSE: skipped - empty response and no file")
                    return
                caption = wrap_links_in_blockquote(best_match.response) if best_match.response else None
                if best_match.file_tg_id:
                    if best_match.file_type == 'photo':
                        await update.message.reply_photo(photo=best_match.file_tg_id, caption=caption, parse_mode='HTML')
                    elif best_match.file_type == 'video':
                        await update.message.reply_video(video=best_match.file_tg_id, caption=caption, parse_mode='HTML')
                    else:
                        await update.message.reply_document(document=best_match.file_tg_id, caption=caption, parse_mode='HTML')
                elif best_match.file_url:
                    if best_match.file_type == 'photo':
                        await update.message.reply_photo(photo=best_match.file_url, caption=caption, parse_mode='HTML')
                    elif best_match.file_type == 'video':
                        await update.message.reply_video(video=best_match.file_url, caption=caption, parse_mode='HTML')
                    else:
                        await update.message.reply_document(document=best_match.file_url, caption=caption, parse_mode='HTML')
                else:
                    await update.message.reply_text(wrap_links_in_blockquote(best_match.response), parse_mode='HTML', disable_web_page_preview=True)
                logger.info("AUTO_RESPONSE: sent successfully")
                await log_activity(
                    action="auto_response",
                    details=f"رد تلقائي على: {text[:50]}...",
                    performed_by=update.effective_user.id if update.effective_user else 0
                )
            except Exception as e:
                logger.warning(f"AUTO_RESPONSE: send error: {e}")
            return
        else:
            logger.info(f"AUTO_RESPONSE: no match found for '{text}'")
    else:
        logger.info("AUTO_RESPONSE: no custom responses in DB")
    
    normalized_text = normalize_arabic(text.lower().strip())
    for keyword, response in DEFAULT_RESPONSES.items():
        kw = normalize_arabic(keyword.lower().strip())
        if kw in normalized_text or (len(normalized_text) >= 3 and normalized_text in kw):
            try:
                await update.message.reply_text(wrap_links_in_blockquote(response), parse_mode='HTML', disable_web_page_preview=True)
            except Exception as e:
                logger.warning(f"Could not send default response: {e}")
            return
    
    questions = await search_question(text)
    if questions:
        if isinstance(questions, list):
            question_result = questions[0] if questions else None
        else:
            question_result = questions
        
        if question_result:
            await increment_question_usage(question_result.id)
            try:
                if question_result.news_id:
                    news_post = await get_news_by_id(question_result.news_id)
                    if news_post:
                        content = wrap_links_in_blockquote(news_post.content or "")
                        if news_post.image_url:
                            await update.message.reply_photo(photo=news_post.image_url, caption=content, parse_mode='HTML')
                        elif news_post.file_url:
                            await update.message.reply_document(document=news_post.file_url, caption=content, parse_mode='HTML')
                        else:
                            await update.message.reply_text(content, parse_mode='HTML', disable_web_page_preview=True)
                        return
                if question_result.file_url:
                    q_answer = wrap_links_in_blockquote(f"❓ {question_result.question}\n\n✅ {question_result.answer}")
                    if question_result.as_document:
                        await update.message.reply_document(document=question_result.file_url, caption=q_answer, parse_mode='HTML')
                    elif question_result.file_type == 'photo':
                        await update.message.reply_photo(photo=question_result.file_url, caption=q_answer, parse_mode='HTML')
                    elif question_result.file_type == 'video':
                        await update.message.reply_video(video=question_result.file_url, caption=q_answer, parse_mode='HTML')
                    else:
                        await update.message.reply_document(document=question_result.file_url, caption=q_answer, parse_mode='HTML')
                else:
                    await update.message.reply_text(wrap_links_in_blockquote(f"❓ {question_result.question}\n\n✅ {question_result.answer}"), parse_mode='HTML', disable_web_page_preview=True)
            except Exception as e:
                logger.warning(f"Could not send question response: {e}")
            await log_activity(
                action="question_answer",
                details=f"إجابة على سؤال: {text[:50]}...",
                performed_by=update.effective_user.id if update.effective_user else 0
            )
            return
    
    ai_fallback_enabled = await get_setting("ai_fallback_enabled")
    if ai_fallback_enabled == "false":
        logger.info("AI fallback disabled by setting, skipping")
        return
    try:
        ai_answer = await asyncio.to_thread(search_university_info, text)
        if ai_answer and ai_answer.strip():
            await update.message.reply_text(wrap_links_in_blockquote(ai_answer.strip()), parse_mode='HTML', disable_web_page_preview=True)
            await log_activity(
                action="ai_fallback",
                details=f"رد AI على: {text[:50]}...",
                performed_by=update.effective_user.id if update.effective_user else 0
            )
    except Exception as e:
        logger.warning(f"AI fallback error: {e}")


auto_response_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auto_response)
