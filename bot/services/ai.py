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


async def _build_post_link(post_obj) -> str | None:
    """Build a t.me link for a post object."""
    import json as _json

    link = None
    if post_obj.channel_message_id and post_obj.target_channels:
        try:
            channels = _json.loads(post_obj.target_channels)
            if channels:
                channel_id = channels[0]
                try:
                    chat = await _bot.get_chat(int(channel_id))
                    if chat.username:
                        link = f"https://t.me/{chat.username}/{post_obj.channel_message_id}"
                    else:
                        link = f"https://t.me/c/{abs(int(channel_id))}/{post_obj.channel_message_id}"
                except Exception as e:
                    logger.warning(f"get_chat failed for {channel_id}: {e}")
                    link = f"https://t.me/c/{abs(int(channel_id))}/{post_obj.channel_message_id}"
        except (_json.JSONDecodeError, TypeError, IndexError, ValueError):
            pass

    if not link and post_obj.group_message_ids:
        try:
            group_ids = _json.loads(post_obj.group_message_ids)
            if group_ids:
                first_chat_id = next(iter(group_ids))
                msg_id = group_ids[first_chat_id]
                if isinstance(msg_id, list):
                    msg_id = msg_id[0] if msg_id else None
                if msg_id:
                    try:
                        chat = await _bot.get_chat(int(first_chat_id))
                        if chat.username:
                            link = f"https://t.me/{chat.username}/{msg_id}"
                        else:
                            link = f"https://t.me/c/{abs(int(first_chat_id))}/{msg_id}"
                    except Exception:
                        link = f"https://t.me/c/{abs(int(first_chat_id))}/{msg_id}"
        except (_json.JSONDecodeError, TypeError, StopIteration, KeyError, ValueError):
            pass

    return link


_SEARCH_PROMPT = """\u0623\u0646\u062a \u0628\u062d\u062b \u0630\u0643\u064a \u0648\u0639\u0645\u064a\u0642 \u0641\u064a \u0645\u0646\u0634\u0648\u0631\u0627\u062a \u062c\u0627\u0645\u0639\u0629 \u0627\u0644\u0645\u0644\u0643 \u062e\u0627\u0644\u062f. \u0645\u0647\u0645\u062a\u0643: \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0646\u0634\u0648\u0631 \u064a\u062c\u064a\u0628 \u0639\u0644\u0649 \u0627\u0644\u0633\u0624\u0627\u0644 \u0628\u0634\u0643\u0644 \u062d\u0631\u0641\u064a \u0648\u0635\u0631\u064a\u062d.

\u26a0\ufe0f \u0642\u0648\u0627\u0639\u062f \u062d\u062f\u064a\u062f\u0629 \u2014 \u0623\u064a \u0627\u0646\u062a\u0647\u0627\u0643 = \u062e\u0637\u0623:
1. \u0623\u062c\u0628 \u0641\u0642\u0637 \u0625\u0630\u0627 \u0648\u062c\u062f\u062a \u0641\u064a \u0627\u0644\u0646\u0635 \u0627\u0644\u062d\u0631\u0641\u064a \u0644\u0644\u0645\u0646\u0634\u0648\u0631 \u0625\u062c\u0627\u0628\u0629 \u0648\u0627\u0636\u062d\u0629 \u0648\u0635\u0631\u064a\u062d\u0629 \u0639\u0644\u0649 \u0627\u0644\u0633\u0624\u0627\u0644
2. \u0644\u0627 \u062a\u064f\u0639\u064a\u062f \u0635\u064a\u0627\u063a\u0629 \u0627\u0644\u0633\u0624\u0627\u0644 \u0648\u062a\u0642\u0648\u0644 "\u0646\u0639\u0645" \u2014 \u064a\u062c\u0628 \u0623\u0646 \u064a\u0643\u0648\u0646 \u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0645\u0643\u062a\u0648\u0628\u0629 \u062d\u0631\u0641\u064a\u064b\u0627 \u0641\u064a \u0627\u0644\u0645\u0646\u0634\u0648\u0631
3. \u0644\u0627 \u062a\u062a\u0648\u0642\u0639 \u0623\u0648 \u062a\u0633\u062a\u0646\u062a\u062c \u0623\u0648 \u062a\u0643\u0645\u0644 \u062c\u0645\u0644\u0629 \u2014 \u0625\u0630\u0627 \u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0644\u064a\u0633\u062a \u0641\u064a \u0627\u0644\u0645\u0646\u0634\u0648\u0631\u060c \u062a\u062e\u0637\u065c \u0627\u0644\u0645\u0646\u0634\u0648\u0631
4. \u0644\u0627 \u062a\u0631\u062f \u0639\u0644\u0649 \u0623\u0633\u0626\u0644\u0629 \u0639\u0627\u0645\u0651\u0629 \u0645\u062b\u0644 "\u0648\u0634 \u0623\u062e\u0628\u0627\u0631 \u0627\u0644\u062c\u0627\u0645\u0639\u0629\u061f" \u0623\u0648 "\u0643\u064a\u0641 \u062d\u0627\u0644\u0643\u0645\u061f" \u2014 \u0647\u0630\u0647 \u0644\u0627 \u062c\u0648\u0627\u0628 \u0644\u0647\u0627 \u0641\u064a \u0627\u0644\u0645\u0646\u0634\u0648\u0631\u0627\u062a
5. \u0644\u0627 \u062a\u0631\u062f \u0639\u0644\u0649 \u0623\u0633\u0626\u0644\u0629 \u0634\u062e\u0635\u064a\u0629 \u0623\u0648 \u0637\u0644\u0628 \u0645\u0633\u0627\u0639\u062f\u0629 \u0625\u062f\u0627\u0631\u064a\u0629 \u2014 \u0641\u0642\u0637 \u0623\u0633\u0626\u0644\u0629 \u0644\u0647\u0627 \u062c\u0648\u0627\u0628 \u0641\u064a \u0627\u0644\u0645\u0646\u0634\u0648\u0631\u0627\u062a
6. \u0625\u0630\u0627 \u0627\u0644\u0633\u0624\u0627\u0644 \u064a\u062a\u0637\u0644\u0628 \u0645\u0639\u0644\u0648\u0645\u0629 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f\u0629 \u0641\u064a \u0623\u064a \u0645\u0646\u0634\u0648\u0631 \u2192 NULL
7. \u0625\u0630\u0627 \u0627\u0644\u0633\u0624\u0627\u0644 \u063a\u0627\u0645\u0636 \u0623\u0648 \u064a\u0642\u0628\u0644 \u0623\u0643\u062b\u0631 \u0645\u0646 \u062a\u0641\u0633\u064a\u0631 \u2192 NULL

\ud83d\udca1 \u0641\u0647\u0645 \u0627\u0644\u0633\u064a\u0627\u0642 \u0648\u0627\u0644\u0646\u064a\u0629:
- "\u0627\u0644\u062a\u062d\u0648\u064a\u0644" \u062a\u0639\u0646\u064a "\u0627\u0644\u062a\u062d\u0648\u064a\u0644 \u0627\u0644\u062f\u0627\u062e\u0644\u064a" \u0639\u0627\u062f\u0629\u064b
- "\u0641\u062a\u062d" \u062a\u0639\u0646\u064a "\u0645\u062a\u0627\u062d/\u0645\u062a\u0635\u0644/\u0645\u0633\u062a\u0645\u0631 \u0627\u0644\u062a\u0633\u062c\u064a\u0644"
- "\u0628\u0643\u0631\u0647" \u062a\u0639\u0646\u064a "\u063a\u062f\u0627\u064b"
- "\u0627\u0644\u0646\u0642\u0644" \u062a\u0639\u0646\u064a "\u0627\u0644\u0646\u0642\u0644\u064a \u0627\u0644\u062f\u0627\u062e\u0644\u064a" \u0639\u0627\u062f\u0629\u064b
- "\u0627\u0644\u062f\u0648\u0631\u0629" \u0623\u0648 "\u0627\u0644\u0643\u0648\u0631\u0633" \u062a\u0639\u0646\u064a "\u0627\u0644\u0641\u0635\u0644 \u0627\u0644\u062f\u0631\u0627\u0633\u064a"
- "\u0627\u0644\u0641\u0627\u0636\u064a" \u062a\u0639\u0646\u064a "\u0627\u0644\u0645\u062a\u0628\u0642\u064a" \u0623\u0648 "\u0627\u0644\u0634\u0627\u063a\u0631"
- "\u0627\u0644\u0625\u0633\u0642\u0627\u0637" \u062a\u0639\u0646\u064a "\u0625\u0633\u0642\u0627\u0637 \u0627\u0644\u0645\u0642\u0631\u0631"
- "\u0627\u0644\u0625\u0639\u0627\u062f\u0629" \u062a\u0639\u0646\u064a "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631"
- "\u0627\u0644\u0645\u0643\u0627\u0641\u0623\u0629" \u062a\u0639\u0646\u064a "\u0627\u0644\u0645\u0643\u0627\u0641\u0623\u0629 \u0627\u0644\u0645\u0627\u0644\u064a\u0629"
- "\u0627\u0644\u062a\u0642\u062f\u064a\u0645" \u062a\u0639\u0646\u064a "\u062a\u0642\u062f\u064a\u0645 \u0637\u0644\u0628"
- "\u0627\u0644\u0642\u0628\u0648\u0644" \u062a\u0639\u0646\u064a "\u0642\u0628\u0648\u0644 \u0637\u0644\u0628"
- "\u0627\u0644\u0645\u0631\u0648\u0631" \u062a\u0639\u0646\u064a "\u0645\u0631\u0648\u0631 \u0627\u0644\u0645\u0642\u0631\u0631" \u0623\u0648 "\u0646\u062c\u0627\u062d \u0627\u0644\u0645\u0642\u0631\u0631"

\u0627\u0644\u0645\u0646\u0634\u0648\u0631\u0627\u062a:
{posts_text}

\u0633\u0624\u0627\u0644 \u0627\u0644\u0637\u0627\u0644\u0628: {query}

\u062e\u0637\u0648\u0627\u062a \u0627\u0644\u062a\u062d\u0642\u0642 (\u0627\u0641\u0639\u0644\u0647\u0627 \u0642\u0628\u0644 \u0627\u0644\u0625\u062c\u0627\u0628\u0629):
- \u0627\u0642\u0631\u0623 \u0643\u0644 \u0645\u0646\u0634\u0648\u0631
- \u0641\u0647\u0645 \u0627\u0644\u0633\u0624\u0627\u0644: \u0645\u0627\u0630\u0627 \u064a\u0631\u064a\u062f \u0627\u0644\u0637\u0627\u0644\u0628 \u0641\u0639\u0644\u0627\u064b\u061f \u0645\u0627 \u0627\u0644\u0633\u064a\u0627\u0642\u061f \u0645\u0627 \u0627\u0644\u0646\u064a\u0629\u061f
- \u0647\u0644 \u064a\u0648\u062c\u062f \u0641\u064a \u0646\u0635 \u0647\u0630\u0627 \u0627\u0644\u0645\u0646\u0634\u0648\u0631 \u062c\u0645\u0644\u0629 \u062a\u062c\u064a\u0628 \u0639\u0644\u0649 \u0627\u0644\u0633\u0624\u0627\u0644 \u062d\u0631\u0641\u064a\u064b\u0627\u061f
- \u0625\u0630\u0627 \u0646\u0639\u0645 \u2192 \u0623\u0631\u062c\u0639 ID \u0648 TITLE
- \u0625\u0630\u0627 \u0644\u0627 \u2192 \u062a\u062e\u0637\u065c \u0648\u0627\u0646\u062a\u0642\u0644 \u0644\u0644\u062a\u0627\u0644\u064a
- \u0625\u0630\u0627 \u0644\u0645 \u062a\u062c\u062f \u0623\u064a \u0645\u0646\u0634\u0648\u0631 \u0641\u064a\u0647 \u0627\u0644\u0625\u062c\u0627\u0628\u0629 \u0627\u0644\u062d\u0631\u0641\u064a\u0651\u0629 \u2192 NULL

\u0627\u0644\u0646\u0627\u062a\u062c (\u0628\u062f\u0648\u0646 \u0623\u064a \u0634\u0631\u062d):
ID: [\u0631\u0642\u0645 \u0627\u0644\u0645\u0646\u0634\u0648\u0631]
TITLE: [\u0627\u0644\u0639\u0646\u0648\u0627\u0646]

\u0623\u0648: NULL"""


async def _ai_select_post(query: str, posts: list) -> dict | None:
    """Ask AI to select the best matching post from a list."""
    import json as _json
    from bot.services.database import cache_response
    from bot.services.response_engine import important_tokens

    if not posts:
        return None

    posts_text = ""
    post_ids = {}
    for i, post in enumerate(posts):
        content = (post.content or "")[:300]
        if content.strip():
            posts_text += f"--- \u0645\u0646\u0634\u0648\u0631 {i+1} (ID: {post.id}) ---\n{content}\n\n"
            post_ids[post.id] = post

    if not posts_text.strip():
        return None

    prompt = _SEARCH_PROMPT.format(posts_text=posts_text, query=query)

    try:
        response = await asyncio.to_thread(_call_model, prompt, thinking=False)
        if not response or not response.strip() or response.strip() == "NULL":
            return None

        lines = response.strip().split("\n")
        post_id = None
        title = None
        for line in lines:
            line = line.strip()
            if line.upper().startswith("ID:"):
                try:
                    post_id = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
            elif line.upper().startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()

        if not post_id or post_id not in post_ids:
            return None

        post_obj = post_ids[post_id]
        post_tokens = set(important_tokens(post_obj.content or ""))
        query_tokens = set(important_tokens(query))
        if not (query_tokens & post_tokens):
            logger.warning(f"AI selected post {post_id} but no token overlap with query")
            return None

        link = await _build_post_link(post_obj)

        await cache_response(query, title, link)
        return {"title": title, "link": link}
    except Exception as e:
        logger.error(f"AI post selection failed: {e}")

    return None


async def search_internal_posts(query: str, limit: int = 50) -> dict | None:
    """
    Search stored news posts using AI to find the best match for a student's query.

    Multi-stage approach:
    - Stage 1: Fetch recent posts (limit)
    - Stage 2: Score by token overlap, sort by relevance
    - Stage 3: Try top 15 first (cheaper, faster)
    - Stage 4: If no match, try remaining posts (deeper search)

    Returns:
        {"title": "...", "link": "https://t.me/..."} if a relevant post is found
        None if no relevant post found
    """
    from bot.services.database import get_cached_response

    cached = await get_cached_response(query)
    if cached:
        logger.info(f"Cache hit for query: {query[:50]}")
        return cached

    from bot.services.database import async_session
    from bot.models.models import News
    from bot.services.response_engine import important_tokens
    from sqlalchemy import select, desc

    async with async_session() as session:
        result = await session.execute(
            select(News)
            .where(News.is_published == True)
            .order_by(desc(News.created_at))
            .limit(limit)
        )
        posts = result.scalars().all()

    if not posts:
        return None

    query_tokens = set(important_tokens(query))
    if not query_tokens:
        return None

    scored = []
    for post in posts:
        content = post.content or ""
        post_tokens = set(important_tokens(content))
        if not post_tokens:
            continue
        overlap = len(query_tokens & post_tokens)
        if overlap > 0:
            score = overlap / len(query_tokens)
            scored.append((score, post))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Stage 1: Try top 15
    top_posts = [post for _, post in scored[:15]]
    result = await _ai_select_post(query, top_posts)
    if result:
        return result

    # Stage 2: Try remaining posts (deeper search)
    remaining = [post for _, post in scored[15:]]
    if remaining:
        result = await _ai_select_post(query, remaining[:30])
        if result:
            return result

    return None
