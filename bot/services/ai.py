import logging
import time as _time

logger = logging.getLogger(__name__)

API_URL = "https://opencode.ai/zen/v1/chat/completions"
API_KEY = "sk-O60vp4JsXJpojOhgWKtExSmBvRk3TEbRVYPiujwribvlsEPUgtaNvGg3ulR8j6Ko"
MODEL = "deepseek-v4-flash-free"
MAX_RETRIES = 3


def _call_model(prompt: str) -> str:
    import httpx

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.3,
                    "extra_body": {
                        "thinking": {"type": "enabled"},
                        "reasoning_effort": "max",
                    },
                },
                timeout=httpx.Timeout(45.0, read=45.0),
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
    prompt = f"""أنت خبير في تحليل المحتوى الإعلامي. حلل خبر الجامعة التالي وأعطني:

1. خمس كلمات مفتاحية مرتبطة بالخبر
2. خمس أسئلة محتملة قد يسألها الطلاب والقراء

عنوان الخبر: {title}
محتوى الخبر: {content}

أجب بالتنسيق التالي بالضبط (بدون أي نص إضافي):

 كلمات مفتاحية:
1. [كلمة1]
2. [كلمة2]
3. [كلمة3]
4. [كلمة4]
5. [كلمة5]

أسئلة:
1. [سؤال1]
2. [سؤال2]
3. [سؤال3]
4. [سؤال4]
5. [سؤال5]"""

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

            if section == "keywords" and len(keywords) < 5:
                keywords.append(item)
            elif section == "questions" and len(questions) < 5:
                questions.append(item)

        return {"keywords": keywords, "questions": questions}
    except Exception as e:
        logger.error(f"AI news analysis failed: {e}")
        raise RuntimeError(f"AI analysis failed: {e}")
