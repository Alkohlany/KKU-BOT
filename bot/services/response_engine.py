"""محرك مطابقة محافظ للردود الطلابية.

الهدف ليس اختيار أي رد قريب، بل اتخاذ واحد من ثلاثة قرارات:
- direct: تطابق قوي وفريد.
- choices: أكثر من موضوع محتمل ويجب أن يختار الطالب.
- none: لا توجد نتيجة موثوقة بما يكفي.

لا يستخدم المحرك الذكاء الاصطناعي ولا يعتمد على المطابقة الضبابية وحدها.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Any, Iterable, Literal
from functools import lru_cache

from bot.config import normalize_arabic


STOP_WORDS = {
    "ا", "او", "ام", "ان", "انا", "انت", "انتي", "احنا", "نحن",
    "اذا", "اذ", "الا", "الى", "الي", "اللي", "الذي", "التي",
    "في", "من", "على", "عن", "مع", "ما", "ماذا", "هذا", "هذه",
    "هو", "هي", "هم", "هل", "وش", "ايش", "كيف", "متى", "وين",
    "اين", "كم", "ليش", "ليه", "لو", "طيب", "ابي", "ابغى", "اريد",
    "ممكن", "يمكن", "راح", "سوف", "صار", "يصير", "يكون", "عندي",
    "عند", "بعد", "قبل", "كل", "اي", "شي", "شيء", "حق", "حقه",
    "جامعه", "الجامعه", "جامعهالملكخالد", "kku", "خالد", "الملك",
}

# توحيد أكثر الصيغجمع/المفرد شيوعاً في أسئلة الطلاب.
TOKEN_EQUIVALENTS = {
    "جداول": "جدول",
    "مواعيد": "موعد",
    "مقررات": "مقرر",
    "مواد": "ماده",
    "رغبات": "رغبه",
    "نتائج": "نتيجه",
    "تخصصات": "تخصص",
    "نسب": "نسبه",
    "معدلات": "معدل",
    "خطط": "خطه",
    "كليات": "كليه",
    "برامج": "برنامج",
    "خدمات": "خدمه",
    "رسائل": "رساله",
    "ترقيات": "ترقيه",
    "اختبارات": "اختبار",
    "قاعات": "قاعه",
    "مباني": "مبني",
    "طلاب": "طالب",
    "طالبات": "طالب",
    "دبلومات": "دبلوم",
    "درجات": "درجه",
    "الوان": "لون",
    "فرص": "فرصه",
    "احجز": "حجز",
    "اسجل": "تسجيل",
    "سجل": "تسجيل",
    "انسحب": "انسحاب",
    "اعتذر": "اعتذار",
}

GENERIC_LABEL_PREFIXES = (
    "هنا تفاصيل",
    "تفاصيل",
    "تنبيه هام جدا",
    "تنبيه هام",
    "تنويه هام",
    "تنويه مهم",
    "توضيح هام جدا",
    "توضيح هام",
)

DISAMBIGUATING_CONTEXT_TERMS = {
    "صيفي", "دبلوم", "ماجستير", "دكتوراه", "نقل", "زائر", "سكن",
    "طب", "صحي", "هندسي", "بلاكبورد", "سيبت", "cept", "مكافاه",
    "رمضان", "رسوم", "تدريب",
}

TIME_SENSITIVE_MARKERS = (
    "باقي 24", "24 ساع", "اليوم", "غدا", "أمس", "امس",
    "اخر موعد", "آخر موعد", "موعد انتهاء", "بدء ارسال", "بدء إرسال",
    "انتهاء المرحله", "انتهاء المرحلة", "من 17 الى 26", "من 17 إلى 26",
)


@dataclass(frozen=True)
class ResponseCandidate:
    response: Any
    score: float
    matched_pattern: str
    exact_terms: int
    fuzzy_terms: int
    exact_phrase: bool


@dataclass(frozen=True)
class MatchDecision:
    action: Literal["direct", "choices", "none"]
    candidates: tuple[ResponseCandidate, ...] = ()
    reason: str = ""

    @property
    def best(self) -> ResponseCandidate | None:
        return self.candidates[0] if self.candidates else None


@lru_cache(maxsize=8192)
def normalize_text(text: str) -> str:
    text = normalize_arabic((text or "").lower())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = "".join(character if (character.isalnum() or character.isspace()) else " " for character in text)
    text = re.sub(r"([\u0600-\u06ff])([0-9a-z])", r"\1 \2", text)
    text = re.sub(r"([0-9a-z])([\u0600-\u06ff])", r"\1 \2", text)
    return " ".join(text.split())


@lru_cache(maxsize=4096)
def _canonical_token(token: str) -> str:
    token = token.strip()
    if token.startswith("لل") and len(token) > 5:
        token = "ال" + token[2:]
    elif token.startswith("بال") and len(token) > 5:
        token = token[1:]
    if token.startswith("ال") and len(token) > 4:
        token = token[2:]

    for suffix in ("هما", "كما", "هم", "هن", "كم", "كن", "ها", "نا", "يه", "ية"):
        suffix = normalize_text(suffix)
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break

    return TOKEN_EQUIVALENTS.get(token, token)


@lru_cache(maxsize=1)
def _normalized_stop_words() -> frozenset[str]:
    return frozenset(normalize_text(word) for word in STOP_WORDS)


@lru_cache(maxsize=8192)
def important_tokens(text: str) -> tuple[str, ...]:
    normalized_stop_words = _normalized_stop_words()
    tokens: list[str] = []
    for raw in normalize_text(text).split():
        token = _canonical_token(raw)
        if not token or token in normalized_stop_words or token.isdigit():
            continue
        if len(token) < 2:
            continue
        if token not in tokens:
            tokens.append(token)
    return tuple(tokens)


@lru_cache(maxsize=4096)
def split_patterns(keyword: str) -> tuple[str, ...]:
    patterns: list[str] = []
    for line in (keyword or "").splitlines():
        line = line.strip(" \t\r\n:-–—•🔻⬇️")
        if line and important_tokens(line):
            patterns.append(line)
    return tuple(patterns)


def _safe_typo_match(left: str, right: str) -> bool:
    """تصحيح إملائي شديد التحفظ.

    يشترط نفس الحرف الأول، وطولاً متقارباً، وتشابهاً 90% فأعلى.
    لا يمكن لهذه المطابقة وحدها أن تنتج إجابة مباشرة.
    """
    if left == right:
        return True
    if min(len(left), len(right)) < 5:
        return False
    if left[0] != right[0] or abs(len(left) - len(right)) > 2:
        return False
    return SequenceMatcher(None, left, right).ratio() >= 0.90


def _ordered_match(query_tokens: tuple[str, ...], pattern_tokens: tuple[str, ...]) -> bool:
    if len(pattern_tokens) < 2:
        return False
    iterator = iter(query_tokens)
    return all(any(candidate == token for candidate in iterator) for token in pattern_tokens)


def _score_tokens(query_tokens: tuple[str, ...], pattern_tokens: tuple[str, ...]) -> tuple[float, int, int]:
    if not query_tokens or not pattern_tokens:
        return 0.0, 0, 0

    remaining_query = list(query_tokens)
    remaining_pattern: list[str] = []
    exact = 0
    fuzzy = 0

    for token in pattern_tokens:
        if token in remaining_query:
            remaining_query.remove(token)
            exact += 1
        else:
            remaining_pattern.append(token)

    if exact:
        for token in remaining_pattern:
            for idx, query_token in enumerate(remaining_query):
                if _safe_typo_match(token, query_token):
                    remaining_query.pop(idx)
                    fuzzy += 1
                    break

    matched = exact + fuzzy
    if matched == 0:
        return 0.0, 0, 0

    query_coverage = matched / len(query_tokens)
    pattern_coverage = matched / len(pattern_tokens)
    exact_quality = exact / matched
    score = 0.55 * query_coverage + 0.35 * pattern_coverage + 0.10 * exact_quality

    if exact >= 2 and query_coverage == 1:
        score = max(score, 0.82)
    elif exact >= 3 and query_coverage >= 0.75:
        score = max(score, 0.78)

    if _ordered_match(query_tokens, pattern_tokens):
        score += 0.04

    return min(score, 0.99), exact, fuzzy


def _score_pattern(query: str, pattern: str) -> tuple[float, int, int, bool]:
    query_norm = normalize_text(query)
    pattern_norm = normalize_text(pattern)
    query_tokens = important_tokens(query)
    pattern_tokens = important_tokens(pattern)

    if not query_tokens or not pattern_tokens:
        return 0.0, 0, 0, False

    if query_norm == pattern_norm:
        return 1.0, len(query_tokens), 0, True

    if len(pattern_tokens) >= 2 and pattern_norm in query_norm:
        return 0.97, len(pattern_tokens), 0, False

    if len(query_tokens) >= 2 and query_norm in pattern_norm:
        score = 0.90 if len(pattern_tokens) <= len(query_tokens) + 2 else 0.84
        return score, len(query_tokens), 0, False

    score, exact, fuzzy = _score_tokens(query_tokens, pattern_tokens)
    return score, exact, fuzzy, False


def _score_response(query: str, response: Any) -> ResponseCandidate | None:
    patterns = split_patterns(getattr(response, "keyword", ""))
    if not patterns:
        return None

    best: ResponseCandidate | None = None
    for pattern in patterns:
        score, exact, fuzzy, exact_phrase = _score_pattern(query, pattern)
        candidate = ResponseCandidate(
            response=response,
            score=score,
            matched_pattern=pattern,
            exact_terms=exact,
            fuzzy_terms=fuzzy,
            exact_phrase=exact_phrase,
        )
        if best is None or (candidate.score, candidate.exact_terms, -candidate.fuzzy_terms) > (
            best.score,
            best.exact_terms,
            -best.fuzzy_terms,
        ):
            best = candidate

    combined_tokens: list[str] = []
    for pattern in patterns:
        for token in important_tokens(pattern):
            if token not in combined_tokens:
                combined_tokens.append(token)
    combined_score, combined_exact, combined_fuzzy = _score_tokens(
        important_tokens(query), tuple(combined_tokens)
    )
    if combined_exact >= 2:
        combined_score = min(0.76, combined_score + 0.04)
        combined_candidate = ResponseCandidate(
            response=response,
            score=combined_score,
            matched_pattern=best.matched_pattern if best else patterns[0],
            exact_terms=combined_exact,
            fuzzy_terms=combined_fuzzy,
            exact_phrase=False,
        )
        if best is None or (combined_candidate.score, combined_candidate.exact_terms) > (
            best.score,
            best.exact_terms,
        ):
            best = combined_candidate
        elif best and combined_exact > best.exact_terms:
            best = replace(
                best,
                score=min(1.0, best.score + 0.012 * (combined_exact - best.exact_terms)),
                exact_terms=combined_exact,
                fuzzy_terms=min(best.fuzzy_terms, combined_fuzzy),
            )

    if best:
        query_context = set(important_tokens(query)) & DISAMBIGUATING_CONTEXT_TERMS
        response_context = set(combined_tokens) & DISAMBIGUATING_CONTEXT_TERMS
        missing_context = response_context - query_context
        if missing_context:
            best = replace(best, score=max(0.0, best.score - min(0.24, 0.14 * len(missing_context))))

    return best if best and best.score > 0 else None


def _response_is_usable(response: Any) -> bool:
    """يرفض السجلات التي لا تحتوي إلا على فواصل وروابط القنوات."""
    if getattr(response, "news_id", None) or getattr(response, "file_tg_id", None) or getattr(response, "file_url", None):
        return True

    text = (getattr(response, "response", "") or "").strip()
    if not text:
        return False

    meaningful_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"[-_=–—•.\s]+", line):
            continue
        if re.search(r"https?://|(?:^|\s)t\.me/|whatsapp\.com/", line, re.IGNORECASE):
            line = re.sub(r"https?://\S+|(?:^|\s)t\.me/\S+|whatsapp\.com/\S+", "", line, flags=re.IGNORECASE).strip()
        if line.startswith("#") or "قروب_جامعة" in line or "قروب جامعة" in line:
            continue
        if line:
            meaningful_lines.append(line)

    return bool(important_tokens(" ".join(meaningful_lines)))


def _response_signature(response: Any) -> tuple[Any, ...]:
    """بصمة المحتوى لمنع عرض منشور واحد مرتين بسبب سجلات مكررة."""
    return (
        normalize_text(getattr(response, "response", "") or ""),
        getattr(response, "news_id", None),
        getattr(response, "file_tg_id", None),
        getattr(response, "file_url", None),
    )


def rank_responses(query: str, responses: Iterable[Any], limit: int = 6) -> list[ResponseCandidate]:
    candidates: list[ResponseCandidate] = []
    for response in responses:
        if not _response_is_usable(response):
            continue
        candidate = _score_response(query, response)
        if candidate:
            candidates.append(candidate)

    def created_sort_value(item: ResponseCandidate) -> float:
        created_at = getattr(item.response, "created_at", None)
        if hasattr(created_at, "timestamp"):
            return float(created_at.timestamp())
        if isinstance(created_at, str):
            try:
                from datetime import datetime
                return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return 0.0
        return 0.0

    candidates.sort(
        key=lambda item: (
            item.score,
            item.exact_phrase,
            item.exact_terms,
            -item.fuzzy_terms,
            created_sort_value(item),
            getattr(item.response, "id", 0),
        ),
        reverse=True,
    )

    unique: list[ResponseCandidate] = []
    seen_signatures: set[tuple[Any, ...]] = set()
    for candidate in candidates:
        signature = _response_signature(candidate.response)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        unique.append(candidate)
        if len(unique) == limit:
            break
    return unique


def decide_match(query: str, responses: Iterable[Any], max_choices: int = 4) -> MatchDecision:
    ranked = rank_responses(query, responses, limit=10)
    if not ranked:
        return MatchDecision("none", reason="no_candidates")

    top = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    margin = top.score - runner.score if runner else top.score
    query_term_count = len(important_tokens(query))

    if (
        top.exact_phrase
        and query_term_count >= 2
        and (runner is None or runner.score < 0.88)
    ):
        return MatchDecision("direct", (top,), "unique_exact_phrase")

    if (
        top.score >= 0.90
        and top.exact_terms >= query_term_count
        and top.fuzzy_terms == 0
        and (runner is None or runner.exact_terms < top.exact_terms)
    ):
        return MatchDecision("direct", (top,), "specific_term_resolved_ambiguity")

    if (
        top.score >= 0.88
        and top.exact_terms >= 2
        and margin >= 0.16
        and top.fuzzy_terms <= 1
    ):
        return MatchDecision("direct", (top,), "high_confidence_unique")

    if (
        top.score >= 0.78
        and top.exact_terms >= 3
        and margin >= 0.20
        and top.fuzzy_terms == 0
    ):
        return MatchDecision("direct", (top,), "strong_token_coverage")

    choice_floor = max(0.20, top.score - 0.24)
    choices: list[ResponseCandidate] = []
    for candidate in ranked:
        if candidate.score < choice_floor or candidate.exact_terms < 1:
            continue
        if top.exact_terms >= 2:
            if candidate.exact_terms < 2 and candidate.score < top.score - 0.08:
                continue
        elif top.exact_phrase and not candidate.exact_phrase and candidate.score < top.score - 0.08:
            continue
        choices.append(candidate)

    if (top.score >= 0.42 or top.exact_terms >= 2 or top.exact_phrase) and choices:
        return MatchDecision("choices", tuple(choices[:max_choices]), "ambiguous_or_medium_confidence")

    return MatchDecision("none", reason="below_safe_threshold")


def response_label(response: Any, matched_pattern: str | None = None, max_length: int = 48) -> str:
    first_line = ""
    response_text = (getattr(response, "response", "") or "").strip()
    if response_text:
        first_line = next((line.strip() for line in response_text.splitlines() if line.strip()), "")

    label = re.sub(r"https?://\S+", "", first_line)
    label = re.sub(r"^[\W_]+", "", label, flags=re.UNICODE).strip()
    generic_prefix_re = re.compile(
        r"^(?:(?:هنا\s+)?تفاصيل|"
        r"(?:تنبيه|تنويه|توضيح)\s+(?:هام|مهم)(?:\s+جد[اً]?)?)"
        r"[\u064b-\u065f\u0670\s:：\-–—]*",
        re.IGNORECASE,
    )
    for _ in range(2):
        cleaned = generic_prefix_re.sub("", label).strip(" :-–—")
        if cleaned == label:
            break
        label = cleaned

    if not label or len(important_tokens(label)) < 2:
        label = (matched_pattern or "").strip()
    if not label:
        label = f"الموضوع رقم {getattr(response, 'id', '')}".strip()

    label = " ".join(label.split())
    return label if len(label) <= max_length else label[: max_length - 1].rstrip() + "…"


def needs_freshness_warning(response: Any) -> bool:
    text = f"{getattr(response, 'keyword', '')}\n{getattr(response, 'response', '')}"
    normalized = normalize_text(text)
    if any(normalize_text(marker) in normalized for marker in TIME_SENSITIVE_MARKERS):
        return True

    temporal_terms = (
        "موعد", "مواعيد", "جدول", "نتائج", "تسجيل", "فتح", "اغلاق",
        "الفصل", "القبول", "التحويل", "الفرص", "ترقيه",
    )
    has_hijri_year = bool(re.search(r"(?:^|\s)14\d{2}(?:\s|$)", normalized))
    has_calendar_term = any(normalize_text(term) in normalized for term in temporal_terms)
    month_names = (
        "يناير", "فبراير", "مارس", "ابريل", "مايو", "يونيو", "يوليو",
        "اغسطس", "سبتمبر", "اكتوبر", "نوفمبر", "ديسمبر",
    )
    return (has_hijri_year and has_calendar_term) or any(month in normalized for month in month_names)
