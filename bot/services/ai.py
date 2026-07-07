import logging
from bot.config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODELS = [
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
]


def _call_model(prompt: str, model: str) -> str:
    import httpx

    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        },
        timeout=30,
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

    last_error = None
    for model in DEFAULT_MODELS:
        try:
            content = _call_model(prompt, model)
            result = content.strip().split("\n")
            items = [line.strip("- ").strip() for line in result if line.strip()]
            if items:
                return items
        except Exception as e:
            last_error = e
            logger.warning(f"AI model {model} failed: {e}")
            continue

    raise RuntimeError(f"All AI models failed. Last error: {last_error}")
