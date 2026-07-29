"""القائمة الطلابية والقوائم الفرعية واختيار النتائج المتشابهة."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from bot.middleware.subscription import subscription_required, verify_subscription
from bot.services.database import get_auto_response_by_id, get_auto_responses, log_activity
from bot.services.response_delivery import send_auto_response
from bot.services.response_engine import ResponseCandidate, rank_responses, response_label
from bot.services.news_publisher import wrap_links_in_blockquote

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MenuTopic:
    label: str
    search_text: str = ""
    preferred_ids: tuple[int, ...] = ()
    action: str = "search"


@dataclass(frozen=True)
class MenuCategory:
    title: str
    description: str
    topics: tuple[MenuTopic, ...]


MENU_CATEGORIES: dict[str, MenuCategory] = {
    "admission": MenuCategory(
        "📋 القبول الجامعي",
        "المواعيد والشروط والرغبات والنتائج ومنصة قبول.",
        (
            MenuTopic("📅 مواعيد القبول", "مواعيد القبول جدول القبول", (363, 365, 372, 370)),
            MenuTopic("📝 شروط ومعايير القبول", "شروط القبول معايير القبول", (420, 222, 249, 290)),
            MenuTopic("🧭 ترتيب وتعديل الرغبات", "ترتيب الرغبات تعديل الرغبات", (373, 284, 285, 424)),
            MenuTopic("✅ تأكيد وإلغاء القبول", "تأكيد القبول إلغاء القبول", (333, 296, 445, 298)),
            MenuTopic("📊 النتائج والترقيات", "نتائج القبول الترقيات", (287, 288, 295, 312)),
            MenuTopic("🎯 الفرص الإضافية", "الفرص الإضافية", (308, 319, 320, 324)),
            MenuTopic("🛠 مشكلات منصة قبول", "مشكلة منصة قبول", (260, 297, 314, 316)),
        ),
    ),
    "registration": MenuCategory(
        "🗓 التسجيل الأكاديمي",
        "المقررات والجداول والحذف والإضافة والفصل الصيفي.",
        (
            MenuTopic("📚 تسجيل المقررات والجداول", "مواعيد تسجيل المقررات جدول المواد", (332, 406, 427)),
            MenuTopic("➕ الحذف والإضافة", "الحذف والإضافة تسجيل المقررات", (427, 426, 353)),
            MenuTopic("☀️ الفصل الصيفي", "الفصل الصيفي المقررات الصيفية", (302, 434)),
            MenuTopic("🔁 الطالب الزائر", "الزائر الداخلي الزائر الخارجي", (415, 439, 427)),
            MenuTopic("📄 توصيف المقررات", "توصيف المقررات", (428,)),
            MenuTopic("🗓 التقويم الأكاديمي", "التقويم الأكاديمي", (411, 218)),
        ),
    ),
    "majors": MenuCategory(
        "🎓 التخصصات والخطط",
        "دليل التخصصات والخطط والمسارات والتخصيص.",
        (
            MenuTopic("📚 الخطط الدراسية", action="plans"),
            MenuTopic("🎓 دليل التخصصات", "دليل التخصصات شروط التخصصات", (392, 249)),
            MenuTopic("🩺 المسار الصحي", "المسار الصحي ضوابط التخصيص", (416, 247)),
            MenuTopic("⚙️ المسار الهندسي", "المسار الهندسي ضوابط التخصيص", (238,)),
            MenuTopic("🩺 مقابلة كلية الطب", "مقابلة كلية الطب", (304,)),
            MenuTopic("🏅 مرتبة الشرف", "مرتبة الشرف", (244,)),
        ),
    ),
    "scores": MenuCategory(
        "📊 النسب والموزونات",
        "نسب القبول والموزونة والمركبة والتقديرات.",
        (
            MenuTopic("📈 نسب القبول", "نسب القبول معدلات القبول", (388, 222)),
            MenuTopic("🧮 الموزونة والمركبة", "الموزونة النسبة المركبة", (451, 247)),
            MenuTopic("🎯 التخصص المناسب للدرجة", "التخصصات المناسبة الدرجة الموزونة", (379,)),
            MenuTopic("📊 معدلات التحويل", "معدلات التحويل أقل معدل", (405, 404, 403, 257)),
            MenuTopic("🔸 الدرجات والتقديرات", "رموز الدرجات التقديرات القريدات", (398, 438)),
            MenuTopic("🚫 الغياب والحرمان", "نسبة الغياب الحرمان", (417,)),
        ),
    ),
    "transfer": MenuCategory(
        "🔄 التحويل",
        "التحويل الداخلي والخارجي والمعدلات والمواعيد.",
        (
            MenuTopic("🔁 التحويل الداخلي", "التحويل الداخلي شروط التحويل", (404, 403, 257, 405)),
            MenuTopic("🌐 التحويل الخارجي", "التحويل الخارجي شروط التحويل", (403, 257)),
            MenuTopic("📅 مواعيد التحويل", "مواعيد التحويل", (404, 403, 257)),
            MenuTopic("📊 معدلات التحويل", "معدلات التحويل أقل معدل", (405, 404, 403, 257)),
            MenuTopic("🏫 الزائر الداخلي", "الزائر الداخلي", (415,)),
            MenuTopic("🌍 الزائر الخارجي", "الزائر الخارجي", (439, 427)),
        ),
    ),
    "actions": MenuCategory(
        "📚 الاعتذار والتأجيل والانسحاب",
        "اختر الإجراء بدقة حتى لا يختلط المقرر بالفصل أو القبول.",
        (
            MenuTopic("📄 الاعتذار عن مقرر", "الاعتذار عن مقرر حذف مادة", (426, 353)),
            MenuTopic("📚 الاعتذار عن فصل", "الاعتذار عن الفصل الدراسي", (273, 262)),
            MenuTopic("⏸ تأجيل الفصل", "تأجيل الفصل الدراسي", (343, 358)),
            MenuTopic("🚪 الانسحاب", "الانسحاب", (397, 445, 298)),
            MenuTopic("🔁 إعادة القيد", "إعادة القيد", (358,)),
        ),
    ),
    "systems": MenuCategory(
        "💻 الأنظمة الإلكترونية",
        "أكاديميا والدخول الموحد والبلاك بورد والرقم الجامعي.",
        (
            MenuTopic("🎓 نظام أكاديميا", "دليل استخدام أكاديميا", (241,)),
            MenuTopic("🔐 الدخول الموحد", "بوابة الدخول الموحد تسجيل الدخول", (293,)),
            MenuTopic("🔢 الرقم والبريد الجامعي", "الرقم الجامعي تفعيل البريد", (442,)),
            MenuTopic("🖥 Blackboard Ultra", "دليل بلاك بورد ألترا", (345, 340, 347)),
            MenuTopic("📝 اختبار CEPT", "اختبار تحديد المستوى CEPT", (292, 335, 342)),
            MenuTopic("🛠 مشكلة تقنية", "مشكلة تسجيل الدخول الخدمات الإلكترونية", (293, 340, 260)),
        ),
    ),
    "campus": MenuCategory(
        "🏫 الكليات والمباني",
        "المباني والقاعات والكليات والسكن والنقل.",
        (
            MenuTopic("🏢 أرقام المباني والقاعات", "أرقام المباني القاعات الفرعاء", (414,)),
            MenuTopic("🏠 السكن الجامعي", "السكن الجامعي", (423,)),
            MenuTopic("🚌 النقل الجامعي", "النقل الجامعي باصات الجامعة", (433,)),
            MenuTopic("🏛 الكليات", "دليل التخصصات والكليات", (392, 289)),
            MenuTopic("📍 مواقع الاختبارات", "مواقع الاختبارات مكان الاختبار", (342, 335)),
        ),
    ),
    "services": MenuCategory(
        "ℹ️ الخدمات الطلابية",
        "المكافأة والإرشاد والرسوم والخدمات العامة.",
        (
            MenuTopic("💰 المكافأة", "المكافأة أسباب انقطاعها", (450,)),
            MenuTopic("👨‍🏫 المرشد الأكاديمي", "حجز موعد المرشد الأكاديمي", (354,)),
            MenuTopic("💳 الرسوم الدراسية", "دفع الرسوم الدراسية", (348,)),
            MenuTopic("☎️ عمادة القبول والتسجيل", "أرقام عمادة القبول والتسجيل", (448,)),
            MenuTopic("🧑‍🎓 خدمات الطلاب", "خدمات الطلاب", (289,)),
            MenuTopic("📝 الاختبار النهائي البديل", "الاختبار النهائي البديل", (355, 337)),
        ),
    ),
}


MAIN_MENU_TEXT = (
    "👋 <b>مرحبًا بك في بوت جامعة الملك خالد</b>\n\n"
    "يمكنك كتابة سؤالك مباشرة، أو اختيار القسم الأقرب من القائمة.\n\n"
    "عندما تكون الإجابة واضحة سيعرضها البوت مباشرة، وعند وجود أكثر من "
    "موضوع متشابه سيطلب منك اختيار المقصود بدل إرسال منشور غير صحيح."
)


def build_main_menu() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    items = list(MENU_CATEGORIES.items())
    for index in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[index][1].title, callback_data=f"menu:cat:{items[index][0]}")]
        if index + 1 < len(items):
            row.append(InlineKeyboardButton(items[index + 1][1].title, callback_data=f"menu:cat:{items[index + 1][0]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def build_category_menu(category_key: str) -> InlineKeyboardMarkup:
    category = MENU_CATEGORIES[category_key]
    rows = [
        [InlineKeyboardButton(topic.label, callback_data=f"menu:topic:{category_key}:{index}")]
        for index, topic in enumerate(category.topics)
    ]
    rows.append([
        InlineKeyboardButton("↩️ رجوع", callback_data="menu:home"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="menu:home"),
    ])
    return InlineKeyboardMarkup(rows)


def _extract_url(text: str) -> str | None:
    match = re.search(r'https?://[^\s<>"]+', text)
    return match.group(0) if match else None


def build_candidate_keyboard(
    candidates: list[ResponseCandidate] | tuple[ResponseCandidate, ...],
    *,
    back_callback: str = "menu:home",
    chat_type: str = "private",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    used_labels: set[str] = set()

    for candidate in candidates[:4]:
        label = response_label(candidate.response, candidate.matched_pattern)
        if label in used_labels:
            pattern_label = response_label(candidate.response, candidate.matched_pattern, max_length=38)
            label = f"{pattern_label} · خيار آخر"
        used_labels.add(label)
        content = candidate.response.response or ""
        url = _extract_url(content)
        if url:
            rows.append([InlineKeyboardButton(label, url=url)])
        else:
            rows.append([
                InlineKeyboardButton(label, callback_data=f"menu:resp:{candidate.response.id}")
            ])

    if chat_type == "private":
        rows.append([
            InlineKeyboardButton("↩️ رجوع", callback_data=back_callback),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="menu:home"),
        ])
    return InlineKeyboardMarkup(rows)


def build_after_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 فتح القائمة الرئيسية", callback_data="menu:home")]])


async def _edit_or_reply(query, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
    except Exception as exc:
        logger.debug("Could not edit menu message, sending a new one: %s", exc)
        await query.message.reply_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        is_subscribed = await subscription_required(update, context)
        if not is_subscribed:
            return
        await update.message.reply_text(
            MAIN_MENU_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=build_main_menu(),
        )


async def _show_topic_results(query, category_key: str, topic: MenuTopic, chat_type: str = "private") -> None:
    responses = await get_auto_responses()

    candidates: list[ResponseCandidate] = []
    if topic.preferred_ids:
        by_id = {response.id: response for response in responses}
        for response_id in topic.preferred_ids:
            response = by_id.get(response_id)
            if not response:
                continue
            patterns = [line.strip() for line in (response.keyword or "").splitlines() if line.strip()]
            candidates.append(
                ResponseCandidate(
                    response=response,
                    score=1.0,
                    matched_pattern=patterns[0] if patterns else topic.search_text,
                    exact_terms=1,
                    fuzzy_terms=0,
                    exact_phrase=False,
                )
            )
            if len(candidates) == 4:
                break

    if not candidates:
        ranked = rank_responses(topic.search_text, responses, limit=10)
        candidates = [
            candidate
            for candidate in ranked
            if candidate.exact_terms >= 1 and candidate.score >= 0.18
        ][:4]

    if not candidates:
        await _edit_or_reply(
            query,
            "لم أجد منشورًا مناسبًا لهذا الموضوع حاليًا. يمكنك الرجوع وكتابة سؤالك بصيغة أوضح.",
            build_category_menu(category_key),
        )
        return

    if len(candidates) == 1:
        response = candidates[0].response
        label = response_label(response, candidates[0].matched_pattern)
        await _edit_or_reply(
            query,
            f"✅ <b>تم اختيار:</b> {escape(label)}\n\nسيظهر المحتوى في الرسالة التالية.",
            build_after_answer_keyboard(),
        )
        sent = await send_auto_response(
            query.message,
            response,
            reply_markup=build_after_answer_keyboard(),
        )
        if sent:
            try:
                await log_activity(
                    action="auto_response_selected",
                    details=json.dumps(
                        {"response_id": response.id, "source": "menu_single_result"},
                        ensure_ascii=False,
                    ),
                    performed_by=query.from_user.id if query.from_user else 0,
                )
            except Exception as exc:
                logger.warning("Could not log single menu response %s: %s", response.id, exc)
        else:
            await query.message.reply_text("تعذر إرسال المحتوى المختار حاليًا.")
        return

    text = (
        f"🔎 <b>{topic.label}</b>\n\n"
        "وجدت الموضوعات التالية. اختر المقصود، ولن يرسل البوت أي منشور قبل اختيارك:"
    )
    await _edit_or_reply(
        query,
        text,
        build_candidate_keyboard(candidates, back_callback=f"menu:cat:{category_key}", chat_type=chat_type),
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    user = update.effective_user
    if user and not await verify_subscription(user.id, context):
        await query.answer("يجب الاشتراك في القناة الرسمية أولاً.", show_alert=True)
        return
    await query.answer()

    data = query.data or ""
    parts = data.split(":")

    if data == "menu:home":
        await _edit_or_reply(query, MAIN_MENU_TEXT, build_main_menu())
        return

    if len(parts) >= 3 and parts[1] == "cat":
        category_key = parts[2]
        category = MENU_CATEGORIES.get(category_key)
        if not category:
            await query.answer("القسم غير موجود", show_alert=True)
            return
        text = f"<b>{category.title}</b>\n\n{category.description}\n\nاختر الموضوع الذي تريد معرفته:"
        await _edit_or_reply(query, text, build_category_menu(category_key))
        return

    if len(parts) >= 4 and parts[1] == "topic":
        category_key = parts[2]
        category = MENU_CATEGORIES.get(category_key)
        if not category:
            await query.answer("القسم غير موجود", show_alert=True)
            return
        try:
            topic = category.topics[int(parts[3])]
        except (ValueError, IndexError):
            await query.answer("الموضوع غير موجود", show_alert=True)
            return

        if topic.action == "plans":
            from bot.handlers.study_plans import get_plans_text

            plans_text = wrap_links_in_blockquote(await get_plans_text())
            await _edit_or_reply(
                query,
                plans_text,
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ رجوع", callback_data=f"menu:cat:{category_key}"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="menu:home"),
                ]]),
            )
            return

        await _show_topic_results(query, category_key, topic, chat_type=update.effective_chat.type)
        return

    if len(parts) >= 3 and parts[1] == "resp":
        try:
            response_id = int(parts[2])
        except ValueError:
            await query.answer("الاختيار غير صالح", show_alert=True)
            return

        response = await get_auto_response_by_id(response_id)
        if not response or not response.is_active:
            await query.answer("هذا الرد لم يعد متاحًا", show_alert=True)
            return

        label = response_label(response)
        await _edit_or_reply(
            query,
            f"✅ <b>تم اختيار:</b> {escape(label)}\n\nسيظهر المحتوى في الرسالة التالية.",
            build_after_answer_keyboard(),
        )
        sent = await send_auto_response(
            query.message,
            response,
            reply_markup=build_after_answer_keyboard(),
        )
        context.user_data.pop("pending_response_query", None)
        try:
            await log_activity(
                action="auto_response_selected",
                details=json.dumps(
                    {"response_id": response.id, "source": "menu_or_ambiguity"},
                    ensure_ascii=False,
                ),
                performed_by=update.effective_user.id if update.effective_user else 0,
            )
        except Exception as exc:
            logger.warning("Could not log selected response %s: %s", response.id, exc)
        if not sent:
            await query.message.reply_text("تعذر إرسال المحتوى المختار حاليًا.")


menu_handler = CommandHandler("menu", menu_command)
menu_text_handler = MessageHandler(filters.Regex(r"^\s*(?:القائمة|القائمه|menu)\s*$"), menu_command)
menu_callback_handler = CallbackQueryHandler(menu_callback, pattern=r"^menu:")
