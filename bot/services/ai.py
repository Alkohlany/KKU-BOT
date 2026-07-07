import httpx
import logging
from bot.config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen-2.5-7b-instruct:free"


def extract_keywords_and_questions(text: str, max_keywords: int = 5, max_questions: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    prompt = f"""اقرأ النص التالي واستخرج منه:
1. {max_keywords} كلمات مفتاحية أساسية تدل على موضوع النص (كلمة واحدة فقط لكل كلمة مفتاحية)
2. {max_questions} أسئلة متوقعة قد يسألها طلاب جامعيون عن هذا الموضوع

النص:
{text}

المطلوب: أعد النتيجة كقائمة فقط، كل عنصر في سطر جديد. الكلمات المفتاحية أولاً ثم الأسئلة.
لاتكتب أي شرح أو مقدمة."""

    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter API error {response.status_code}: {response.text}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("OpenRouter returned no choices")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("OpenRouter returned empty content")

    result = content.strip().split("\n")
    items = [line.strip("- ").strip() for line in result if line.strip()]
    return items
