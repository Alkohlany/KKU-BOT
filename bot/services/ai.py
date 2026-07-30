import asyncio
import logging
import re
import time as _time
import base64
from bot.config import OPENCODE_AI_MODEL, OPENCODE_API_URL, OPENCODE_API_KEY, BOT_TOKEN
from telegram import Bot as _TGBot

_bot = _TGBot(token=BOT_TOKEN)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _call_model(prompt: str, image_bytes: bytes = None, mime_type: str = "image/jpeg", thinking: bool = True) -> str:
    import httpx

    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{image_b64}"
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
        max_tokens = 4000
        timeout_s = 120.0
    else:
        content = prompt
        max_tokens = 3000
        timeout_s = 90.0

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(
                OPENCODE_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENCODE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENCODE_AI_MODEL,
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": max_tokens,
                    **({"extra_body": {
                        "thinking": {"type": "enabled"},
                        "reasoning_effort": "max",
                    }} if thinking else {}),
                },
                timeout=httpx.Timeout(timeout_s, read=timeout_s),
            )

            if response.status_code == 503:
                logger.warning(f"API overloaded (503), retry {attempt+1}/{MAX_RETRIES}")
                _time.sleep(2 * (attempt + 1))
                continue

            if response.status_code != 200:
                raise RuntimeError(f"API error {response.status_code}: {response.text[:200]}")

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("no choices returned")

            result = choices[0].get("message", {}).get("content", "")
            if not result:
                raise RuntimeError("empty content returned")

            return result
        except httpx.TimeoutException:
            logger.warning(f"API timeout, retry {attempt+1}/{MAX_RETRIES}")
            _time.sleep(2 * (attempt + 1))
            last_err = RuntimeError(f"Timeout after {MAX_RETRIES} attempts")
            continue
        except Exception as e:
            last_err = e
            break

    raise last_err or RuntimeError(f"API failed after {MAX_RETRIES} retries")


def search_university_info(query: str) -> str:
    import httpx
    import re

    search_results_text = ""
    fetched_content = []

    try:
        from ddgs import DDGS
        logger.info(f"Searching DuckDuckGo for: {query}")
        results = DDGS().text(f"{query} جامعة الملك خالد", max_results=5)
        if results:
            formatted = []
            for r in results[:5]:
                title = r.get("title", "")
                body = r.get("body", "")
                url = r.get("href", "")
                formatted.append(f"- {title}: {body} (source: {url})")
                if url and ("kku" in url or "edu.sa" in url):
                    try:
                        resp = httpx.get(url, timeout=httpx.Timeout(10.0, read=10.0), follow_redirects=True)
                        if resp.status_code == 200:
                            text = re.sub('<[^<]+?>', ' ', resp.text)
                            text = re.sub(r'\s+', ' ', text).strip()
                            text = text[:2000]
                            if text:
                                fetched_content.append(f"[من {url}]: {text}")
                    except Exception:
                        pass
            search_results_text = "\n".join(formatted)
            logger.info(f"DuckDuckGo returned {len(results)} results, fetched {len(fetched_content)} pages")
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")

    combined = ""
    if search_results_text and fetched_content:
        combined = f"نتائج البحث:\n{search_results_text}\n\nمحتوى من الصفحات:\n" + "\n\n".join(fetched_content)
    elif search_results_text:
        combined = f"نتائج البحث:\n{search_results_text}"
    elif fetched_content:
        combined = "محتوى من الصفحات:\n" + "\n\n".join(fetched_content)

    if combined:
        prompt = f"""أنت مساعد ذكي في جامعة الملك خالد. استخدم المعلومات التالية للإجابة:
{combined}
السؤال: {query}
أجب بشكل مفصل (5-8 جمل). اذكر المصادر والروابط."""
    else:
        logger.warning("DuckDuckGo failed, using AI knowledge")
        prompt = f"""أنت مساعد ذكي في جامعة الملك خالد. السؤال: {query}
أجب بناءً على معرفتك. لا تقل "لا أستطيع البحث"."""

    try:
        return _call_model(prompt)
    except Exception as e:
        logger.warning(f"AI university search failed: {e}")
        return "عذراً، حدث خطأ أثناء البحث. حاول مرة أخرى."


BLOCKED_WORDS = {
    "القواعد", "مهمة", "استخرج", "النصوص", "إذا", "النص",
    "قصير", "أعد", "أضف", "مثل", "ركّز", "التفاصيل",
    "المحددة", "مثال", "الرد", "النتيجة", "شرح", "عنوان",
}


def _clean_item(item: str) -> str:
    item = item.strip().strip("- •*")
    item = item.strip()
    if item.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
        item = item.split(".", 1)[1].strip()
    return item


def _is_valid(item: str) -> bool:
    if not item or len(item) < 2:
        return False
    if len(item) > 100:
        return False
    item_lower = item.lower()
    for blocked in BLOCKED_WORDS:
        if blocked in item_lower:
            return False
    if item.endswith((":", "؟", "?", "!")):
        pass
    return True


def generate_news_analysis(title: str, content: str) -> dict:
    prompt = f"""أنت محلل محتوى وخبير في فهم نية الباحث (Search Intent)، ومتخصص في الأخبار الجامعية السعودية، خصوصًا أخبار جامعة الملك خالد.

مهمتك ليست تلخيص الخبر، بل تحليله واستخراج أكثر الكلمات المفتاحية والأسئلة التي قد يبحث عنها الطالب بعد قراءة الخبر.

قبل الإجابة، حلّل الخبر داخليًا (دون إظهار التحليل)، ثم استخرج النتائج.

## قواعد الكلمات المفتاحية

* استخرج فقط الكلمات أو العبارات القصيرة المهمة.
* لا تكرر نفس المعنى.
* لا تستخدم كلمات عامة مثل:
  خبر، جامعة، طالب، إعلان، جديد.
* أعطِ الأولوية للمصطلحات التي سيبحث عنها الطالب فعلًا.
* إذا كان اسم جهة أو برنامج أو خدمة هو محور الخبر فاجعله كلمة مفتاحية.
* يمكن أن تكون الكلمة المفتاحية من كلمة إلى ثلاث كلمات.
* رتب الكلمات حسب أهميتها.

## قواعد الأسئلة

تخيّل أنك حللت آلاف عمليات البحث الخاصة بالطلاب.

استخرج أكثر الأسئلة احتمالًا، وليس أي أسئلة عشوائية.

الأسئلة يجب أن تكون:

* باللهجة السعودية البيضاء.
* قصيرة وواضحة.
* طبيعية جدًا.
* مرتبطة مباشرة بالخبر.
* متنوعة بحيث لا تكرر نفس الفكرة.

ركز على أسئلة مثل:

* وش المقصود؟
* متى؟
* وين؟
* كيف؟
* مين؟
* هل يشملني؟
* كيف أسجل؟
* متى يبدأ؟
* وش الشروط؟
* وش الفائدة؟

إذا لم تكن الإجابة موجودة داخل الخبر، فلا بأس، لأن المطلوب هو توقع ما قد يبحث عنه الطالب.

## ممنوع

* لا تؤلف معلومات.
* لا تجيب عن الأسئلة.
* لا تذكر الروابط.
* لا تذكر الهاشتاقات.
* لا تذكر القناة.
* لا تنسخ جملًا من الخبر.

## الأولوية

1. استخرج موضوع الخبر الحقيقي.
2. حدد ما قد يهم الطالب.
3. توقع نية البحث.
4. اكتب النتائج فقط.

عنوان الخبر:
{title}

محتوى الخبر:
{content}

قبل كتابة الإجابة اسأل نفسك داخليًا:

- ما الموضوع الحقيقي للخبر؟
- ما أهم معلومة فيه؟
- ماذا سيكتب الطالب في بحث تيليجرام أو جوجل؟
- ما أول سؤال سيسأله؟
- ما أكثر 5 كلمات ستساعد في العثور على هذا الخبر؟
- هل يوجد تكرار؟
- هل يمكن جعل السؤال أقصر وأكثر طبيعية؟

ثم اكتب النتيجة فقط، ولا تعرض طريقة التفكير.
أعد النتيجة بهذا الشكل فقط:

كلمات مفتاحية:
1.
2.
3.
4.
5.

أسئلة:
1.
2.
3.
4.
5."""

    try:
        content = _call_model(prompt)
        keywords = []
        questions = []

        lines = content.strip().split("\n")
        section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "كلمات مفتاحية" in line.lower() or "keywords" in line.lower():
                section = "keywords"
                continue
            elif "أسئلة" in line.lower() or "questions" in line.lower():
                section = "questions"
                continue

            item = _clean_item(line)
            if not item or not _is_valid(item):
                continue

            if item.startswith('#') or item.startswith('http') or 't.me/' in item:
                continue

            if section == "keywords" and len(keywords) < 5:
                keywords.append(item)
            elif section == "questions" and len(questions) < 5:
                questions.append(item)

        return {"keywords": keywords, "questions": questions}
    except Exception as e:
        logger.error(f"AI news analysis failed: {e}")
        raise RuntimeError(f"AI analysis failed: {e}")


def enhance_content(title: str, content: str) -> dict:
    """Enhance publication content using AI"""
    prompt = f"""# محرر منشورات تيليجرام سعودي احترافي

أنت محرر محتوى محترف، ولست كاتبًا يعيد تأليف النص.

مهمتك هي **تحرير المنشور** وتحسينه ليبدو وكأنه صادر من مسؤول قناة تيليجرام سعودية احترافية، مع الحفاظ على هوية النص ومضمونه.

## القاعدة الذهبية

حسّن... ولا تؤلف.

أي معلومة غير موجودة في النص الأصلي ممنوع إضافتها.

---

## أولًا: حافظ على المحتوى

* لا تغيّر المعنى.
* لا تضف أي معلومة أو رأي أو استنتاج.
* لا تحذف أي معلومة مهمة.
* لا تغيّر التواريخ أو الأرقام أو الأسماء أو الروابط.
* إذا كان النص خبرًا رسميًا فليبقَ خبرًا رسميًا.
* إذا كان النص تنبيهًا فليبقَ تنبيهًا.
* لا تحوّل الخبر إلى إعلان أو رسالة تحفيزية.

---

## ثانيًا: أسلوب الكتابة

استخدم لهجة سعودية بيضاء خفيفة ومناسبة للنشر الرسمي، بحيث تبدو طبيعية للقارئ السعودي دون مبالغة.

الأسلوب المطلوب:

* واضح.
* مختصر.
* احترافي.
* مباشر.
* سهل القراءة.

وتجنب:

* المبالغة.
* التسويق.
* العبارات الإنشائية.

---

## ثالثًا: ممنوع إضافة عبارات مثل

لا تضف من نفسك أي عبارات مثل:

* لا يفوتكم
* سارعوا
* بادروا
* فرصة رائعة
* اليوم
* بإذن الله
* هدف البرنامج
* ننصحكم
* لا تنسون
* انتبهوا (إلا إذا كان المنشور تحذيرًا فعلًا)
* أي دعوة لاتخاذ إجراء غير موجودة بالنص.

---

## رابعًا: التحرير

قم فقط بـ:

* تصحيح الأخطاء الإملائية.
* تحسين علامات الترقيم.
* إعادة ترتيب الجمل إذا لزم الأمر.
* إزالة التكرار.
* جعل القراءة أكثر سلاسة.
* إبراز أهم معلومة في البداية.

إذا كان النص جيدًا أصلًا، فاكتفِ بتحسينات بسيطة.

---

## خامسًا: التنسيق

* استخدم مسافات بين الفقرات.
* استخدم الإيموجي عند الحاجة فقط، وبحد أقصى 3 رموز في المنشور.
* لا تستخدم الإيموجي لمجرد الزينة.
* أبرز الأرقام والتواريخ المهمة بخط عريض إذا كانت المنصة تدعم ذلك.

---

## سادسًا: الروابط والهاشتاقات

* لا تغيّر الروابط.
* لا تغيّر الهاشتاقات.
* ضعها في نهاية المنشور كما هي.

---

## سابعًا: جودة الإخراج

بعد الانتهاء، اسأل نفسك:

* هل أضفت معلومة ليست موجودة؟ إذا نعم، احذفها.
* هل غيّرت نبرة المنشور؟ إذا نعم، أعدها كما كانت.
* هل أصبح النص أسهل للقراءة؟ إذا لا، حسّن التنسيق فقط.
* هل يبدو المنشور وكأنه صادر من مسؤول قناة محترف؟ إذا نعم، فهذا هو الناتج المطلوب.

---

## قاعدة اللغة العربية الإلزامية

* اكتب المنشور باللغة العربية فقط.
* يمنع استخدام أي كلمة أو مصطلح باللغة الإنجليزية داخل النص النهائي.
* إذا ظهر أي مصطلح إنجليزي في النص الأصلي، قم بتحويله إلى المقابل العربي المناسب.
* لا تستخدم كلمات مثل:

  * Opportunities
  * Program
  * Update
  * Link
  * Platform
  * Application
  * وغيرها من الكلمات الإنجليزية.

استخدم دائمًا المصطلحات العربية:

* Opportunities → الفرص الإضافية
* Program → برنامج
* Update → تحديث / إشعار جديد
* Link → رابط
* Platform → منصة
* Application → طلب / تطبيق (حسب السياق)

قبل إخراج النتيجة النهائية، راجع النص وتأكد من عدم وجود أي حرف أو كلمة إنجليزية، إلا إذا كانت جزءًا من رابط إلكتروني أو اسم رسمي لا يمكن تغييره.
بعد الانتهاء من التحرير، قم بمراجعة لغوية نهائية للنص: صحح أي خلط بين العربية والإنجليزية، وتأكد أن جميع الكلمات مكتوبة بالعربية وبأسلوب سعودي طبيعي.

---

## الناتج النهائي

أخرج المنشور النهائي فقط.

لا تكتب:

* إليك النسخة المحسنة.
* تم التحسين.
* بعد إعادة الصياغة.
* أي شرح أو ملاحظات.

المطلوب هو النص الجاهز للنشر فقط.

فكر كمحرر صحفي، لا ككاتب محتوى. إذا كانت الجملة جيدة فلا تغيّرها. لا تبحث عن تغيير النص، بل ابحث عن تحسينه بأقل عدد ممكن من التعديلات التي تحقق أكبر أثر في الوضوح والجمال.
رتّب المعلومات حسب أهميتها، وليس حسب ترتيبها في النص الأصلي. اجعل المعلومة الأكثر تأثيرًا أو الأكثر إلحاحًا في بداية المنشور، ثم رتّب بقية المعلومات من الأهم إلى الأقل أهمية، مع الحفاظ على جميع التفاصيل دون إضافة أو حذف.
محتوى المنشور:
{content}"""

    try:
        enhanced = _call_model(prompt)
        return {"enhanced_content": enhanced.strip()}
    except Exception as e:
        logger.error(f"AI enhance failed: {e}")
        raise RuntimeError(f"AI enhance failed: {e}")


# ---------------------------------------------------------------------------
# Internal-post semantic search
# ---------------------------------------------------------------------------

_SEARCH_STOPWORDS = {
    "ابغى", "ابغي", "ابي", "أبي", "اريد", "أريد", "احتاج", "أحتاج",
    "وش", "ايش", "إيش", "ما", "ماذا", "هل", "كيف", "متى", "وين", "اين", "أين",
    "من", "في", "على", "عن", "الى", "إلى", "مع", "هذا", "هذه", "هذي", "ذا",
    "اللي", "الي", "الذي", "التي", "انا", "أنا", "عندي", "عليه", "عليها",
    "لو", "اذا", "إذا", "طيب", "يعني", "ممكن", "فضلا", "فضلًا", "تكفون",
    "جامعة", "الجامعة", "الملك", "خالد",  # سياق ثابت للبوت، لا يميز المنشورات غالبًا
    "https", "http", "www", "com", "t", "me",
}

_ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]"
)
_NON_SEARCH_CHARS_RE = re.compile(r"[^0-9a-zA-Z\u0621-\u063A\u0641-\u064A\u0660-\u0669\u06F0-\u06F9]+")


def _normalize_search_text(value: object) -> str:
    """Normalize Arabic text for retrieval only; never use it as displayed text."""
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = _ARABIC_DIACRITICS_RE.sub("", text)
    text = text.replace("ـ", "")
    text = text.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ى": "ي", "ؤ": "و", "ئ": "ي", "ة": "ه",
    }))
    text = _NON_SEARCH_CHARS_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _token_variants(token: str) -> set[str]:
    """Generate conservative Arabic variants to improve recall without full stemming."""
    variants = {token}

    if token.startswith("ال") and len(token) >= 5:
        variants.add(token[2:])

    # Common conjunction/preposition prefixes. Keep the original token as well.
    if token[:1] in {"و", "ف", "ب", "ك", "ل"} and len(token) >= 5:
        variants.add(token[1:])
        if token[1:].startswith("ال") and len(token) >= 7:
            variants.add(token[3:])

    for suffix in ("يات", "ات", "ون", "ين", "ها", "هم", "هن", "كم", "نا"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            variants.add(token[:-len(suffix)])

    return {v for v in variants if len(v) >= 2}


def _search_tokens(text: object, important_tokens_fn=None) -> set[str]:
    normalized = _normalize_search_text(text)
    tokens: set[str] = set()

    for raw_token in normalized.split():
        if len(raw_token) < 2 or raw_token in _SEARCH_STOPWORDS:
            continue
        tokens.update(_token_variants(raw_token))

    # Preserve the project's existing tokenizer as an additional signal.
    if important_tokens_fn is not None:
        try:
            for item in important_tokens_fn(str(text or "")) or []:
                for raw_token in _normalize_search_text(item).split():
                    if len(raw_token) >= 2 and raw_token not in _SEARCH_STOPWORDS:
                        tokens.update(_token_variants(raw_token))
        except Exception as exc:
            logger.debug(f"important_tokens failed during semantic search: {exc}")

    return tokens


def _coerce_search_field(value: object) -> str:
    """Convert optional JSON/list/model fields into searchable text safely."""
    if value is None:
        return ""
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return ""
        if raw[:1] in {"[", "{"}:
            try:
                import json
                return _coerce_search_field(json.loads(raw))
            except Exception:
                return raw
        return raw
    if isinstance(value, dict):
        return " ".join(_coerce_search_field(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_coerce_search_field(v) for v in value)
    return str(value)


def _post_search_document(post) -> dict:
    """Build a schema-tolerant searchable document from a News model instance."""
    title = _coerce_search_field(getattr(post, "title", ""))
    content = _coerce_search_field(getattr(post, "content", ""))

    metadata_parts = []
    for attr in (
        "keywords", "questions", "search_keywords", "search_questions",
        "analysis_keywords", "analysis_questions", "summary", "category",
    ):
        value = _coerce_search_field(getattr(post, attr, ""))
        if value:
            metadata_parts.append(value)

    metadata = "\n".join(metadata_parts)
    full_text = "\n".join(part for part in (title, content, metadata) if part)
    return {
        "post": post,
        "title": title,
        "content": content,
        "metadata": metadata,
        "full_text": full_text,
        "normalized": _normalize_search_text(full_text),
    }


def _extract_json_object(raw: str) -> dict | None:
    """Parse a JSON object even when the model wraps it in a Markdown fence."""
    if not raw:
        return None

    import json

    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        parsed = json.loads(cleaned[start:end + 1])
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _clean_analysis_list(value: object, max_items: int = 10) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []

    result = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        normalized = _normalize_search_text(text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(text[:120])
        if len(result) >= max_items:
            break
    return result


async def _analyze_internal_search_query(query: str, important_tokens_fn=None) -> dict:
    """Use the model to convert a Saudi student question into retrieval constraints."""
    fallback_terms = sorted(_search_tokens(query, important_tokens_fn))
    fallback = {
        "searchable": bool(fallback_terms),
        "intent": "بحث عن معلومة أو إرشاد مرتبط بالسؤال",
        "answer_type": "information",
        "core_concepts": fallback_terms[:8],
        "must_have": fallback_terms[:4],
        "should_have": fallback_terms[4:10],
        "entities": [],
        "phrases": [],
        "aliases": [],
        "ambiguity": "medium",
    }

    prompt = f"""أنت محلل استعلامات بحث داخلية لطلاب جامعة الملك خالد.
لا تجب عن سؤال الطالب. حوّل السؤال فقط إلى خطة بحث دقيقة في منشورات عربية.

افهم اللهجة السعودية، الأخطاء الإملائية، الاختصارات، والفرق بين النيات المتقاربة.
أمثلة مهمة:
- "كيف أنسحب من منصة قبول؟" = إجراء الانسحاب من منصة قبول.
- "هل أنسحب من منصة قبول؟" = قرار/نصيحة عن الانسحاب، وليس خطوات الإجراء.
- "هل الانسحاب يسبب حرمان سنتين؟" = أثر أو لائحة الحرمان بعد الانسحاب.
- لا تخلط بين الانسحاب من منصة قبول، والانسحاب من الجامعة، والاعتذار عن فصل.

أخرج JSON صحيحًا فقط بهذه البنية:
{{
  "searchable": true,
  "intent": "وصف قصير ودقيق للنية",
  "answer_type": "procedure|date|condition|eligibility|decision|consequence|definition|location|announcement|information",
  "core_concepts": ["المفاهيم الأساسية"],
  "must_have": ["مفاهيم يجب أن يتناولها المنشور"],
  "should_have": ["مفاهيم مساعدة"],
  "entities": ["أسماء المنصات أو البرامج أو الجهات"],
  "phrases": ["عبارات بحث محتملة"],
  "aliases": ["مرادفات وصيغ سعودية أو إملائية"],
  "ambiguity": "low|medium|high"
}}

اجعل searchable=false فقط للتحية، الكلام العام جدًا، أو السؤال الذي لا يحمل موضوعًا يمكن البحث عنه.
لا تضف معلومات غير موجودة في السؤال، ولا تفترض فصلًا أو برنامجًا أو فئة لم يذكرها الطالب.

سؤال الطالب:
{query}"""

    try:
        raw = await asyncio.to_thread(_call_model, prompt, thinking=False)
        parsed = _extract_json_object(raw)
        if not parsed:
            return fallback

        analysis = {
            "searchable": bool(parsed.get("searchable", True)),
            "intent": str(parsed.get("intent") or fallback["intent"])[:240],
            "answer_type": str(parsed.get("answer_type") or "information")[:40],
            "core_concepts": _clean_analysis_list(parsed.get("core_concepts"), 10),
            "must_have": _clean_analysis_list(parsed.get("must_have"), 8),
            "should_have": _clean_analysis_list(parsed.get("should_have"), 10),
            "entities": _clean_analysis_list(parsed.get("entities"), 8),
            "phrases": _clean_analysis_list(parsed.get("phrases"), 10),
            "aliases": _clean_analysis_list(parsed.get("aliases"), 12),
            "ambiguity": str(parsed.get("ambiguity") or "medium").lower(),
        }

        # A model occasionally returns empty arrays. Never lose the original query signal.
        if not analysis["core_concepts"]:
            analysis["core_concepts"] = fallback["core_concepts"]
        if not analysis["must_have"]:
            analysis["must_have"] = fallback["must_have"]

        return analysis
    except Exception as exc:
        logger.warning(f"Query analysis failed, using lexical fallback: {exc}")
        return fallback


def _term_is_present(term: str, document_tokens: set[str]) -> bool:
    normalized = _normalize_search_text(term)
    if not normalized:
        return False
    variants = set()
    for token in normalized.split():
        variants.update(_token_variants(token))
    return bool(variants & document_tokens)


def _fuzzy_term_coverage(query_terms: set[str], document_tokens: set[str]) -> float:
    """Small typo-tolerance signal; exact/semantic signals remain dominant."""
    from difflib import SequenceMatcher

    useful_query = [t for t in query_terms if len(t) >= 4]
    useful_doc = [t for t in document_tokens if len(t) >= 4]
    if not useful_query or not useful_doc:
        return 0.0

    matched = 0
    for query_token in useful_query:
        if query_token in document_tokens:
            matched += 1
            continue

        best = 0.0
        for doc_token in useful_doc:
            if abs(len(query_token) - len(doc_token)) > 3:
                continue
            if query_token[0] != doc_token[0]:
                continue
            ratio = SequenceMatcher(None, query_token, doc_token).ratio()
            if ratio > best:
                best = ratio
            if best >= 0.92:
                break
        if best >= 0.84:
            matched += 1

    return matched / max(1, len(useful_query))


def _candidate_snippet(content: str, search_terms: set[str], max_chars: int = 2200) -> str:
    """Select the most query-relevant paragraphs while preserving their original wording."""
    content = (content or "").strip()
    if len(content) <= max_chars:
        return content

    paragraphs = [p.strip() for p in re.split(r"\n{2,}|(?<=[.!؟])\s+", content) if p.strip()]
    scored = []
    for index, paragraph in enumerate(paragraphs):
        tokens = _search_tokens(paragraph)
        overlap = len(tokens & search_terms)
        phrase_bonus = sum(1 for term in search_terms if term in _normalize_search_text(paragraph))
        score = overlap * 3 + phrase_bonus
        scored.append((score, index, paragraph))

    selected = sorted(scored, key=lambda item: (item[0], -item[1]), reverse=True)[:6]
    selected.sort(key=lambda item: item[1])
    snippet = "\n".join(item[2] for item in selected if item[0] > 0)

    if not snippet:
        snippet = content[:max_chars]
    elif len(snippet) > max_chars:
        snippet = snippet[:max_chars]

    return snippet.strip()


def _derive_post_title(post, model_title: str = "") -> str:
    stored_title = _coerce_search_field(getattr(post, "title", "")).strip()
    if stored_title:
        return stored_title[:180]

    content = _coerce_search_field(getattr(post, "content", "")).strip()
    for line in content.splitlines():
        line = line.strip().strip("-*•# ")
        if 8 <= len(line) <= 180 and not line.startswith(("http://", "https://")):
            return line

    model_title = (model_title or "").strip()
    return model_title[:180] or "منشور مرتبط بسؤالك"


def _telegram_private_channel_id(chat_id: object) -> str:
    """Convert -100xxxxxxxxxx IDs to Telegram's /c/xxxxxxxxxx form."""
    raw = str(abs(int(chat_id)))
    return raw[3:] if raw.startswith("100") and len(raw) > 3 else raw


async def _build_internal_post_link(post) -> str | None:
    import json

    async def link_for(chat_id, message_id) -> str | None:
        if not chat_id or not message_id:
            return None
        try:
            chat = await _bot.get_chat(int(chat_id))
            if chat.username:
                return f"https://t.me/{chat.username}/{message_id}"
        except Exception as exc:
            logger.warning(f"get_chat failed for {chat_id}: {exc}")
        try:
            return f"https://t.me/c/{_telegram_private_channel_id(chat_id)}/{message_id}"
        except (TypeError, ValueError):
            return None

    channel_message_id = getattr(post, "channel_message_id", None)
    target_channels = getattr(post, "target_channels", None)
    if channel_message_id and target_channels:
        try:
            channels = json.loads(target_channels) if isinstance(target_channels, str) else target_channels
            if isinstance(channels, (list, tuple)) and channels:
                link = await link_for(channels[0], channel_message_id)
                if link:
                    return link
        except (json.JSONDecodeError, TypeError, ValueError, IndexError):
            pass

    group_message_ids = getattr(post, "group_message_ids", None)
    if group_message_ids:
        try:
            groups = json.loads(group_message_ids) if isinstance(group_message_ids, str) else group_message_ids
            if isinstance(groups, dict) and groups:
                first_chat_id, message_id = next(iter(groups.items()))
                if isinstance(message_id, list):
                    message_id = message_id[0] if message_id else None
                link = await link_for(first_chat_id, message_id)
                if link:
                    return link
        except (json.JSONDecodeError, TypeError, ValueError, StopIteration):
            pass

    return None


async def search_internal_posts(query: str, limit: int = 50) -> dict | None:
    """
    Hybrid Arabic semantic search over stored university posts.

    Pipeline:
      1) normalize and understand the student's intent;
      2) retrieve candidates using weighted lexical, phrase, entity, and fuzzy signals;
      3) ask the model to rerank only the strongest candidates;
      4) verify the selected ID, confidence, evidence, and required concepts locally.

    The public return schema intentionally remains unchanged:
        {"title": "...", "link": "https://t.me/..."}
        None when no sufficiently relevant post exists.
    """
    from collections import Counter
    import math
    import json

    from bot.services.database import get_cached_response, cache_response, async_session
    from bot.models.models import News
    from bot.services.response_engine import important_tokens
    from sqlalchemy import select, desc

    original_query = (query or "").strip()
    normalized_query = _normalize_search_text(original_query)
    if len(normalized_query) < 2:
        return None

    # Versioned normalized key prevents old weak-search cache entries from leaking into v2.
    cache_key = f"internal-search:v2:{normalized_query}"
    cached = await get_cached_response(cache_key)
    if cached:
        logger.info(f"Internal semantic cache hit: {normalized_query[:80]}")
        return cached

    analysis = await _analyze_internal_search_query(original_query, important_tokens)
    if not analysis.get("searchable", True):
        logger.info(f"Query marked non-searchable: {original_query[:80]}")
        return None

    # Scan a meaningful corpus even when legacy callers still pass limit=50.
    # Keep an upper bound to avoid loading an unbounded table into memory.
    scan_limit = min(max(int(limit or 0), 600), 1200)

    async with async_session() as session:
        result = await session.execute(
            select(News)
            .where(News.is_published.is_(True))
            .order_by(desc(News.created_at))
            .limit(scan_limit)
        )
        db_posts = result.scalars().all()

    if not db_posts:
        return None

    phrase_inputs = (
        analysis.get("phrases", [])
        + analysis.get("entities", [])
        + analysis.get("core_concepts", [])
    )
    normalized_phrases = [
        _normalize_search_text(item)
        for item in phrase_inputs
        if _normalize_search_text(item)
    ]

    expanded_text = " ".join(
        [original_query]
        + analysis.get("core_concepts", [])
        + analysis.get("must_have", [])
        + analysis.get("should_have", [])
        + analysis.get("entities", [])
        + analysis.get("aliases", [])
    )
    expanded_terms = _search_tokens(expanded_text, important_tokens)
    original_terms = _search_tokens(original_query, important_tokens)
    must_have = analysis.get("must_have", [])
    entities = analysis.get("entities", [])

    if not expanded_terms:
        return None

    documents = []
    document_frequency = Counter()
    for post in db_posts:
        document = _post_search_document(post)
        if not document["content"].strip():
            continue

        document["tokens"] = _search_tokens(document["full_text"], important_tokens)
        document["title_tokens"] = _search_tokens(document["title"], important_tokens)
        if not document["tokens"]:
            continue

        for term in expanded_terms & document["tokens"]:
            document_frequency[term] += 1
        documents.append(document)

    if not documents:
        return None

    corpus_size = len(documents)
    idf = {
        term: math.log((corpus_size + 1) / (document_frequency.get(term, 0) + 1)) + 1.0
        for term in expanded_terms
    }
    total_query_weight = sum(idf.values()) or 1.0

    candidates = []
    for document in documents:
        doc_tokens = document["tokens"]
        matched_terms = expanded_terms & doc_tokens
        exact_coverage = sum(idf[t] for t in matched_terms) / total_query_weight

        original_coverage = (
            len(original_terms & doc_tokens) / max(1, len(original_terms))
            if original_terms else 0.0
        )
        title_coverage = (
            len(expanded_terms & document["title_tokens"]) / max(1, len(expanded_terms))
        )

        must_matches = sum(1 for term in must_have if _term_is_present(term, doc_tokens))
        must_coverage = must_matches / max(1, len(must_have)) if must_have else 1.0

        entity_matches = sum(1 for term in entities if _term_is_present(term, doc_tokens))
        entity_coverage = entity_matches / max(1, len(entities)) if entities else 0.0

        phrase_hits = sum(
            1 for phrase in normalized_phrases
            if len(phrase) >= 3 and phrase in document["normalized"]
        )
        phrase_coverage = phrase_hits / max(1, len(normalized_phrases))

        fuzzy_coverage = _fuzzy_term_coverage(original_terms - doc_tokens, doc_tokens)
        exact_query_bonus = 1.0 if normalized_query in document["normalized"] else 0.0

        score = (
            0.42 * exact_coverage
            + 0.18 * original_coverage
            + 0.14 * must_coverage
            + 0.08 * entity_coverage
            + 0.08 * phrase_coverage
            + 0.05 * title_coverage
            + 0.03 * fuzzy_coverage
            + 0.02 * exact_query_bonus
        )

        # Missing all required concepts should be a strong negative, not an automatic
        # rejection, because the model may have expressed one concept as a phrase.
        if must_have and must_coverage == 0:
            score *= 0.35

        has_retrieval_signal = bool(matched_terms or phrase_hits or fuzzy_coverage >= 0.34)
        if has_retrieval_signal and score >= 0.055:
            document["retrieval_score"] = round(score, 6)
            document["matched_terms"] = sorted(matched_terms)
            candidates.append(document)

    candidates.sort(key=lambda item: item["retrieval_score"], reverse=True)
    candidates = candidates[:14]

    if not candidates:
        logger.info(f"No internal candidates for query: {original_query[:80]}")
        return None

    candidate_blocks = []
    candidate_ids = set()
    candidate_by_id = {}
    for rank, document in enumerate(candidates, start=1):
        post = document["post"]
        post_id = int(post.id)
        candidate_ids.add(post_id)
        candidate_by_id[post_id] = document

        snippet = _candidate_snippet(document["content"], expanded_terms, max_chars=2200)
        stored_title = document["title"] or "بدون عنوان مخزن"
        candidate_blocks.append(
            f"""--- المرشح {rank} ---
ID: {post_id}
RETRIEVAL_SCORE: {document['retrieval_score']}
STORED_TITLE: {stored_title}
CONTENT:
{snippet}"""
        )

    rerank_prompt = f"""أنت محرك إعادة ترتيب دقيق لمنشورات جامعة الملك خالد.
المطلوب اختيار منشور واحد فقط يخدم نية الطالب الحقيقية، أو رفض جميع المرشحين.

تحليل السؤال:
{json.dumps(analysis, ensure_ascii=False)}

سؤال الطالب:
{original_query}

قواعد المطابقة:
1. افهم المقصود لا مجرد الكلمات المشتركة.
2. فضّل المنشور الذي يجيب مباشرة عن السؤال.
3. يمكن قبول "إرشاد شديد الصلة" إذا كان يعالج نفس الفعل أو القرار الذي يسأل عنه الطالب مباشرة، حتى لو لم يذكر خطوات حرفية.
4. ارفض المنشور الذي يتحدث عن نفس الموضوع لكنه يجيب عن نية مختلفة؛ مثل تاريخ التقديم بدل شروطه، أو الانسحاب من الجامعة بدل الانسحاب من منصة قبول.
5. طابق القيود المهمة بدقة: الجهة، المنصة، البرنامج، نوع القبول، الفئة، الفرع، الجنس، الفصل، التاريخ، والحالة الأكاديمية إن ذُكرت.
6. لا تستنتج لائحة أو حكمًا غير موجود. لا تجعل التشابه العام إجابة.
7. supporting_quote يجب أن يكون اقتباسًا حرفيًا قصيرًا موجودًا داخل CONTENT للمنشور المختار.
8. confidence يعبر عن مدى تطابق المنشور مع نية السؤال، لا عن جودة صياغة المنشور.

حدود القبول:
- direct_answer: لا يقل confidence عن 0.80
- relevant_guidance: لا يقل confidence عن 0.90
- عند الشك أو تعارض القيود اختر none.

المرشحون:
{chr(10).join(candidate_blocks)}

أخرج JSON صحيحًا فقط:
{{
  "match": true,
  "post_id": 123,
  "match_type": "direct_answer|relevant_guidance|none",
  "confidence": 0.0,
  "title": "عنوان وصفي قصير دون اختراع معلومة",
  "supporting_quote": "اقتباس حرفي من المنشور",
  "reason": "سبب داخلي مختصر للمراجعة"
}}

إذا لم يوجد تطابق قوي:
{{"match": false, "post_id": null, "match_type": "none", "confidence": 0.0, "title": "", "supporting_quote": "", "reason": ""}}"""

    try:
        raw_response = await asyncio.to_thread(_call_model, rerank_prompt, thinking=True)
        decision = _extract_json_object(raw_response)
        if not decision or not bool(decision.get("match")):
            return None

        try:
            selected_id = int(decision.get("post_id"))
            confidence = float(decision.get("confidence", 0.0))
        except (TypeError, ValueError):
            return None

        match_type = str(decision.get("match_type") or "none").strip().lower()
        required_confidence = 0.90 if match_type == "relevant_guidance" else 0.80
        if match_type not in {"direct_answer", "relevant_guidance"}:
            return None
        if selected_id not in candidate_ids or confidence < required_confidence:
            logger.info(
                f"Rejected reranker decision id={selected_id}, type={match_type}, "
                f"confidence={confidence:.3f}"
            )
            return None

        selected = candidate_by_id[selected_id]
        selected_post = selected["post"]

        # Local guard 1: evidence must be a real quote from the selected post.
        quote = str(decision.get("supporting_quote") or "").strip()
        normalized_quote = _normalize_search_text(quote)
        if len(normalized_quote) < 8 or normalized_quote not in selected["normalized"]:
            logger.warning(f"Rejected post {selected_id}: supporting quote is not verbatim")
            return None

        # Local guard 2: at least part of the original question or a required concept
        # must exist in the selected document. This blocks model-only hallucinated matches.
        original_overlap = original_terms & selected["tokens"]
        must_matches = sum(1 for term in must_have if _term_is_present(term, selected["tokens"]))
        if not original_overlap and must_matches == 0:
            logger.warning(f"Rejected post {selected_id}: no grounded query concept overlap")
            return None

        title = _derive_post_title(selected_post, str(decision.get("title") or ""))
        link = await _build_internal_post_link(selected_post)
        result = {"title": title, "link": link}

        await cache_response(cache_key, result["title"], result.get("link"))
        logger.info(
            f"Internal semantic match query={original_query[:70]!r} post={selected_id} "
            f"type={match_type} confidence={confidence:.3f} "
            f"retrieval={selected['retrieval_score']:.3f}"
        )
        return result

    except Exception as exc:
        logger.error(f"Internal semantic post search failed: {exc}", exc_info=True)
        return None