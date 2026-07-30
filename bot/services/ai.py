import asyncio
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


async def search_internal_posts(query: str, limit: int = 10) -> dict | None:
    """
    Search stored news posts using AI to find the best match for a student's query.

    Returns:
        {"title": "...", "link": "https://t.me/..."} if a relevant post is found
        None if no relevant post found
    """
    from bot.services.database import async_session
    from bot.models.models import News
    from sqlalchemy import select, desc
    import json as _json

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

    posts_text = ""
    post_ids = []
    for i, post in enumerate(posts):
        content = post.content or ""
        if content.strip():
            posts_text += f"--- منشور {i+1} (ID: {post.id}) ---\n{content}\n\n"
            post_ids.append(post.id)

    if not posts_text.strip():
        return None

    prompt = f"""أنت مساعد ذكي لجامعة الملك خالد. لديك مجموعة منشورات مخزنة في قاعدة البيانات.

المنشورات المتاحة:
{posts_text}

سؤال الطالب: {query}

مهمتك:
1. اقرأ سؤال الطالب بعناية
2. ابحث في المنشورات عن الأنسب لسؤاله — كن متسامحًا، إذا كان المنشور متعلقًا حتى 부분ًا فاحسبه مناسبًا
3. فهم سياق السؤال ضمن جامعة الملك خالد (قبول، تقديم، معدل، نظام، خدمات، إلخ)
4. إذا كان السؤال قصيرًا أو غامضًا (مثلاً: "التقديم"، "القبول"، "المعدل"، "التسجيل")، ابحث عن أي منشور متعلق بالموضوع العام للسؤال

قواعد مهمة:
- لا تخترع معلومات
- إذا كان السؤال عامًا جدًا أو غير متعلق بالجامعة، أرجع NULL
- لا ترفض منشورًا لمجرد أن السؤال قصير — ابحث عن أي علاقة موضوعية

أرجع النتيجة بهذا الشكل بالضبط:
ID: [رقم المنشور]
TITLE: [عنوان مختصر 5-10 كلمات يلخص موضوع المنشور]

إذا لا يوجد مناسب، اكتب: NULL"""

    try:
        response = await asyncio.to_thread(_call_model, prompt)
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

        link = None
        post_obj = next((p for p in posts if p.id == post_id), None)
        if post_obj:
            if post_obj.channel_message_id and post_obj.target_channels:
                try:
                    channels = _json.loads(post_obj.target_channels)
                    if channels:
                        channel_chat_id = channels[0]
                        link = f"https://t.me/c/{abs(int(channel_chat_id))}/{post_obj.channel_message_id}"
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
                            link = f"https://t.me/c/{abs(int(first_chat_id))}/{msg_id}"
                except (_json.JSONDecodeError, TypeError, StopIteration, KeyError, ValueError):
                    pass

        return {"title": title or "منشور متعلق بسؤالك", "link": link}
    except Exception as e:
        logger.error(f"Internal post search failed: {e}")

    return None
