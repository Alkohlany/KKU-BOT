import logging
import re
import time as _time
import base64
from bot.config import OPENCODE_AI_MODEL, OPENCODE_API_URL, OPENCODE_API_KEY

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _call_model(prompt: str, image_bytes: bytes = None, mime_type: str = "image/jpeg") -> str:
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
                    "extra_body": {
                        "thinking": {"type": "enabled"},
                        "reasoning_effort": "max",
                    },
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

## الناتج النهائي

أخرج المنشور النهائي فقط.

لا تكتب:

* إليك النسخة المحسنة.
* تم التحسين.
* بعد إعادة الصياغة.
* أي شرح أو ملاحظات.

المطلوب هو النص الجاهز للنشر فقط.

فكر كمحرر صحفي، لا ككاتب محتوى. إذا كانت الجملة جيدة فلا تغيّرها. لا تبحث عن تغيير النص، بل ابحث عن تحسينه بأقل عدد ممكن من التعديلات التي تحقق أكبر أثر في الوضوح والجمال.

محتوى المنشور:
{content}"""

    try:
        enhanced = _call_model(prompt)
        return {"enhanced_content": enhanced.strip()}
    except Exception as e:
        logger.error(f"AI enhance failed: {e}")
        raise RuntimeError(f"AI enhance failed: {e}")
