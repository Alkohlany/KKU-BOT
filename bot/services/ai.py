import logging
import re
import time as _time
import base64
from bot.config import OPENCODE_AI_MODEL, OPENCODE_API_URL, OPENCODE_API_KEY

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _call_model(prompt: str) -> str:
    import httpx

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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3000,
                    "extra_body": {
                        "thinking": {"type": "enabled"},
                        "reasoning_effort": "max",
                    },
                },
                timeout=httpx.Timeout(90.0, read=90.0),
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

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError("empty content returned")

            return content
        except httpx.TimeoutException:
            logger.warning(f"API timeout, retry {attempt+1}/{MAX_RETRIES}")
            _time.sleep(2 * (attempt + 1))
            last_err = RuntimeError(f"Timeout after {MAX_RETRIES} attempts")
            continue
        except Exception as e:
            last_err = e
            break

    raise last_err or RuntimeError(f"API failed after {MAX_RETRIES} retries")


def _call_model_with_image(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    import httpx

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{mime_type};base64,{image_b64}"

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
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_url}},
                            ],
                        }
                    ],
                    "max_tokens": 4000,
                    "extra_body": {
                        "thinking": {"type": "enabled"},
                        "reasoning_effort": "max",
                    },
                },
                timeout=httpx.Timeout(120.0, read=120.0),
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

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError("empty content returned")

            return content
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


def extract_keywords_and_questions(text: str, max_keywords: int = 5, max_questions: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    total = max_keywords + max_questions

    prompt = f"""أنت طالب سعودي في قروب تيليجرام.

حلل هذا النص وأعطني كلمات مفتاحية وأسئلة باللهجة السعودية:

"{text}"

 الرد خمس أسطر فقط، كل سطر كلمة أو سؤال."""

    try:
        content = _call_model(prompt)
        raw_lines = content.strip().split("\n")
        cleaned = []
        seen = set()
        for line in raw_lines:
            item = _clean_item(line)
            if item and _is_valid(item) and item not in seen:
                seen.add(item)
                cleaned.append(item)
        return cleaned[:total]
    except Exception as e:
        logger.error(f"AI failed: {e}")
        raise RuntimeError(f"AI analysis failed: {e}")


def generate_news_analysis(title: str, content: str) -> dict:
    prompt = f"""أنت طالب في جامعة الملك خالد، ما تفهم بالخبر وتبغى تسأل أسئلة مثل أي طالب عادي.

⚠️ تعليمات مهمة:
- تصرف مثل الطالب اللي ما فهم الخبر ويبغى يستفسر
- اخترع أسئلة قد تخطر على بال أي طالب يبحث عن هذا الموضوع
- الكلمات المفتاحية تكون كلمات وحدها فقط (بدون جمل)
- الأسئلة تكون باللهجة السعودية
- لا تذكر روابط أو هاشتاقات أو إعلانات
- ركّز على الموضوع الرئيسي للخبر

عنوان الخبر: {title}
محتوى الخبر: {content}

أجب بالشكل هذا بالضبط (بدون أي كلام زيادة):

كلمات مفتاحية:
1. كلمة1
2. كلمة2
3. كلمة3
4. كلمة4
5. كلمة5

أسئلة:
1. سؤال1
2. سؤال2
3. سؤال3
4. سؤال4
5. سؤال5"""

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


def enhance_content(title: str, content: str, image_bytes: bytes = None, mime_type: str = None) -> dict:
    """Enhance publication content using AI with optional image analysis"""
    has_image = image_bytes and len(image_bytes) > 0

    if has_image:
        prompt = f"""أنت محرر نصوص متخصص في محتوى تليجرام لجامعة الملك خالد (KKU).

مهمتك: تحسين النص التالي من حيث:
- إصلاح الأخطاء الإملائية والنحوية فقط
- تحسين الصياغة إذا كانت جملة غير واضحة أو طويلة جداً

ما لا تفعله (مهم جداً):
- لا تضيف جمل ختامية مثل "نتمنى لكم التوفيق" أو "مع خالص التحية"
- لا تغير نبرة النص أو أسلوبه (عامي يبقى عامي، رسمي يبقى رسمي)
- لا تحذف أو تغير أي إيموجي أو رابط أو هاشتاق أو رقم قروب
- لا تغير ترتيب الأسطر أو تضيف فراغات جديدة
- لا تضف محتوى أو معلومات جديدة
- إذا كان النص سليم، أرجعه كما هو بدون أي تغيير

حلل الصورة المرفقة: إذا وُجدت في النص معلومات عن الصورة، أضف وصفاً مختصراً لها في مكانها المناسب. إذا لم تكن الصورة مذكورة في النص، لا تضف شيئاً عنها.

محتوى المنشور:
{content}

أرجع النص المحسّن فقط، بدون شرح أو تعليقات:"""
    else:
        prompt = f"""أنت محرر نصوص متخصص في محتوى تليجرام لجامعة الملك خالد (KKU).

مهمتك: تحسين النص التالي من حيث:
- إصلاح الأخطاء الإملائية والنحوية فقط
- تحسين الصياغة إذا كانت جملة غير واضحة أو طويلة جداً

ما لا تفعله (مهم جداً):
- لا تضيف جمل ختامية مثل "نتمنى لكم التوفيق" أو "مع خالص التحية"
- لا تغير نبرة النص أو أسلوبه (عامي يبقى عامي، رسمي يبقى رسمي)
- لا تحذف أو تغير أي إيموجي أو رابط أو هاشتاق أو رقم قروب
- لا تغير ترتيب الأسطر أو تضيف فراغات جديدة
- لا تضف محتوى أو معلومات جديدة
- إذا كان النص سليم، أرجعه كما هو بدون أي تغيير

محتوى المنشور:
{content}

أرجع النص المحسّن فقط، بدون شرح أو تعليقات:"""

    try:
        if has_image:
            enhanced = _call_model_with_image(prompt, image_bytes, mime_type)
        else:
            enhanced = _call_model(prompt)
        return {"enhanced_content": enhanced.strip()}
    except Exception as e:
        logger.error(f"AI enhance failed: {e}")
        raise RuntimeError(f"AI enhance failed: {e}")
