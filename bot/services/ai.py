import logging
from bot.config import NVIDIA_API_KEY

logger = logging.getLogger(__name__)

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODELS = [
    "meta/llama-3.1-8b-instruct",
    "nvidia/nemotron-mini-4b-instruct",
]


def _call_model(prompt: str, model: str) -> str:
    import httpx

    response = httpx.post(
        NVIDIA_NIM_URL,
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        },
        timeout=httpx.Timeout(60.0, read=60.0),
    )

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


BLOCKED_WORDS = {
    "تسجيل", "موعد", "نقل", "جامعة", "كلية", "طالب", "عام", "دليل",
    "قروب", "قناة", "رابط", "تيليجرام", "واتساب", "الملك", "خالد",
    "السعودية", "سنة", "1447", "القواعد", "مهمة", "استخرج", "النصوص",
    "إذا", "النص", "قصير", "أعد", "أضف", "كلمات", "عامة",
    "مثل", "ركّز", "التفاصيل", "المحددة", "فقط", "مثال",
    "الرد", "النتيجة", "السؤال", "الإجابة", "شرح", "عنوان",
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

    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    total = max_keywords + max_questions

    prompt = f"""أنت طالب سعودي في قروب تيليجرام.

حلل هذا النص وأعطني كلمات مفتاحية وأسئلة باللهجة السعودية:

"{text}"

الرد خمس أسطر فقط، كل سطر كلمة أو سؤال."""

    last_error = None
    for model in DEFAULT_MODELS:
        try:
            content = _call_model(prompt, model)
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
            last_error = e
            logger.warning(f"AI model {model} failed: {e}")
            continue

    raise RuntimeError(f"All AI models failed. Last error: {last_error}")
