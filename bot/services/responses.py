from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.config import normalize_arabic
from bot.handlers.student_menu import build_candidate_keyboard, build_main_menu
from bot.services.ai import search_internal_posts, search_university_info
from bot.services.database import (
    get_all_questions,
    get_auto_responses,
    get_setting,
    increment_question_usage,
    log_activity,
)
from bot.services.news_publisher import wrap_links_in_blockquote
from bot.services.response_delivery import send_auto_response
from bot.services.response_engine import decide_match, normalize_text

logger = logging.getLogger(__name__)


GREETING_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 🌙",
    "السلام": "وعليكم السلام ورحمة الله 🌙",
    "اهلا وسهلا": "أهلاً وسهلاً بك 💚",
    "اهلا": "أهلاً وسهلاً بك 💚",
    "مرحبا": "مرحباً بك في جامعة الملك خالد 🎓",
    "صباح الخير": "صباح النور ☀️",
    "مساء الخير": "مساء النور 🌙",
}

COURTESY_RESPONSES = {
    "شكرا": "العفو، نحن في الخدمة 💚",
    "يعطيك العافيه": "وإياك، الله يعطيك العافية 🌸",
}

_GREETING_PATTERN = re.compile(
    r"^\s*(السلام\s+عليكم(?:\s+ورحمة\s+الله(?:\s+وبركاته)?)?|السلام|"
    r"أهلا(?:\s+وسهلا)?|اهلا(?:\s+وسهلا)?|مرحبا|صباح\s+الخير|مساء\s+الخير)"
    r"(?![\u0600-\u06FF])\s*[،,:؛.!؟?\-–—]*\s*",
    re.IGNORECASE,
)

PENDING_TTL_SECONDS = 10 * 60



def _extract_greeting(text: str) -> tuple[str | None, str]:
    match = _GREETING_PATTERN.match(text or "")
    if not match:
        return None, (text or "").strip()

    greeting_key = normalize_text(match.group(1))
    greeting = GREETING_RESPONSES.get(greeting_key)
    if not greeting and greeting_key.startswith(normalize_text("السلام عليكم")):
        greeting = GREETING_RESPONSES["السلام عليكم"]
    elif not greeting and greeting_key == normalize_text("السلام"):
        greeting = GREETING_RESPONSES["السلام"]
    elif not greeting and greeting_key.startswith(normalize_text("اهلا")):
        greeting = GREETING_RESPONSES["اهلا"]

    return greeting, text[match.end():].strip()


def _is_reply_to_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    reply = update.message.reply_to_message if update.message else None
    return bool(reply and reply.from_user and reply.from_user.id == context.bot.id)


def _pending_query(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> str:
    pending = context.user_data.get("pending_response_query")
    if not pending:
        return text

    now = datetime.now(timezone.utc).timestamp()
    if pending.get("expires_at", 0) < now or pending.get("chat_id") != update.effective_chat.id:
        context.user_data.pop("pending_response_query", None)
        return text

    short_follow_up = len(normalize_text(text).split()) <= 6
    if _is_reply_to_bot(update, context) or (update.effective_chat.type == "private" and short_follow_up):
        return f"{pending.get('query', '')} {text}".strip()
    return text


async def _send_safe_question_if_exact(update: Update, text: str) -> bool:
    """جدول questions غير مستخدم حالياً؛ نحافظ عليه بتطابق حرفي آمن فقط."""
    normalized = normalize_text(text)
    questions = await get_all_questions()
    matches = []
    for question in questions:
        phrases = [question.question]
        phrases.extend((question.keywords or "").splitlines())
        if any(normalize_text(phrase) == normalized for phrase in phrases if phrase.strip()):
            matches.append(question)

    if len(matches) != 1:
        return False

    question = matches[0]
    await increment_question_usage(question.id)
    answer = wrap_links_in_blockquote(f"❓ {question.question}\n\n✅ {question.answer}")
    if question.file_url:
        if question.file_type == "photo" and not question.as_document:
            await update.message.reply_photo(photo=question.file_url, caption=answer, parse_mode="HTML")
        elif question.file_type == "video" and not question.as_document:
            await update.message.reply_video(video=question.file_url, caption=answer, parse_mode="HTML")
        else:
            await update.message.reply_document(document=question.file_url, caption=answer, parse_mode="HTML")
    else:
        await update.message.reply_text(answer, parse_mode="HTML", disable_web_page_preview=True)
    return True


async def _log_decision(update: Update, action: str, payload: dict) -> None:
    try:
        await log_activity(
            action=action,
            details=json.dumps(payload, ensure_ascii=False),
            performed_by=update.effective_user.id if update.effective_user else 0,
        )
    except Exception as exc:
        logger.warning("Could not log response decision %s: %s", action, exc)


async def handle_auto_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة محافظـة: إجابة مؤكدة، خيارات، أو صمت/قائمة عند غياب التطابق."""
    if not update.message or not update.message.text:
        return

    if update.message.forward_from_chat or update.message.forward_from:
        return
    if update.effective_user and update.effective_user.id == context.bot.id:
        return

    original_text = update.message.text.strip()
    if not original_text or len(original_text) < 2 or len(original_text) > 500:
        return

    from bot.handlers.study_plans import is_study_plan_request

    if is_study_plan_request(original_text):
        return

    greeting, text = _extract_greeting(original_text)
    if not text:
        await update.message.reply_text(greeting or "مرحباً بك 💚")
        return

    courtesy = COURTESY_RESPONSES.get(normalize_text(text))
    if courtesy:
        await update.message.reply_text(courtesy)
        return

    effective_text = _pending_query(update, context, text)

    # AI internal search in stored posts
    try:
        ai_internal_enabled = await get_setting("ai_internal_search_enabled")
        if ai_internal_enabled != "false":  # enabled by default
            internal_result = await search_internal_posts(effective_text)
            if internal_result:
                reply = f"📌 {internal_result['title']}"
                if internal_result.get("link"):
                    reply += f"\n\n🔗 اضغط هنا للذهاب للمنشور: {internal_result['link']}"
                await update.message.reply_text(reply, disable_web_page_preview=True)
                await _log_decision(update, "ai_internal_search", {"query": text[:100], "found": True})
                return
    except Exception as e:
        logger.error(f"AI internal search error: {e}")

    responses = await get_auto_responses()
    decision = decide_match(effective_text, responses)

    logger.info(
        "SAFE_RESPONSE: text=%r action=%s candidates=%s",
        effective_text,
        decision.action,
        [
            (candidate.response.id, round(candidate.score, 3), candidate.matched_pattern)
            for candidate in decision.candidates
        ],
    )

    if decision.action == "direct" and decision.best:
        best = decision.best
        sent = await send_auto_response(update.message, best.response, prefix=greeting)
        if sent:
            context.user_data.pop("pending_response_query", None)
            await _log_decision(
                update,
                "auto_response",
                {
                    "input": original_text[:250],
                    "effective_query": effective_text[:250],
                    "response_id": best.response.id,
                    "matched_pattern": best.matched_pattern,
                    "match_method": decision.reason,
                    "score": round(best.score, 4),
                    "exact_terms": best.exact_terms,
                    "fuzzy_terms": best.fuzzy_terms,
                },
            )
        return

    if decision.action == "choices" and decision.candidates:
        context.user_data["pending_response_query"] = {
            "query": effective_text,
            "chat_id": update.effective_chat.id,
            "expires_at": datetime.now(timezone.utc).timestamp() + PENDING_TTL_SECONDS,
            "candidate_ids": [candidate.response.id for candidate in decision.candidates],
        }
        prefix = f"{greeting}\n\n" if greeting else ""
        ambiguity_text = (
            "🔎 وجدت أكثر من موضوع قريب من سؤالك.\n\n"
            if len(decision.candidates) > 1
            else "🔎 وجدت موضوعًا قريبًا، لكن التطابق غير مؤكد.\n\n"
        )
        await update.message.reply_text(
            prefix
            + ambiguity_text
            + "اختر المقصود من الأزرار التالية:",
            reply_markup=build_candidate_keyboard(list(decision.candidates), chat_type=update.effective_chat.type),
        )
        await _log_decision(
            update,
            "auto_response_choices",
            {
                "input": original_text[:250],
                "effective_query": effective_text[:250],
                "reason": decision.reason,
                "candidates": [
                    {
                        "response_id": candidate.response.id,
                        "score": round(candidate.score, 4),
                        "matched_pattern": candidate.matched_pattern,
                    }
                    for candidate in decision.candidates
                ],
            },
        )
        return

    if await _send_safe_question_if_exact(update, effective_text):
        return

    ai_fallback_enabled = await get_setting("ai_fallback_enabled")
    if ai_fallback_enabled and ai_fallback_enabled.lower() == "true":
        try:
            ai_answer = await asyncio.to_thread(search_university_info, effective_text)
            if ai_answer and ai_answer.strip():
                await update.message.reply_text(
                    wrap_links_in_blockquote(ai_answer.strip()),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                await _log_decision(update, "ai_fallback", {"input": original_text[:250]})
                return
        except Exception as exc:
            logger.warning("AI fallback error: %s", exc)

    if update.effective_chat.type == "private":
        prefix = f"{greeting}\n\n" if greeting else ""
        await update.message.reply_text(
            prefix
            + "لم أجد نتيجة مؤكدة لهذا السؤال، لذلك لن أرسل منشورًا قد لا يكون مقصودك.\n\n"
            + "اختر القسم الأقرب أو أعد كتابة السؤال مع ذكر الإجراء بالتحديد:",
            reply_markup=build_main_menu(),
        )
        await _log_decision(
            update,
            "auto_response_no_match",
            {"input": original_text[:250], "effective_query": effective_text[:250]},
        )


auto_response_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auto_response)
