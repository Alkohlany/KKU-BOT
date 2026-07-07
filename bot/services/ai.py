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


def extract_keywords_and_questions(text: str, max_keywords: int = 5, max_questions: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    prompt = f"""حلل النص التالي واستخرج منه كلمات مفتاحية وأسئلة باللهجة السعودية.

النص:
{text}

---

القواعد مهمة جداً:
1. استخرج الكلمات والأسئلة من النص فقط، لا تخترع شيء
2. إذا النص قصير أو عام، أعد fewer من 5 (قد يكون 2 أو 3 فقط)
3. لا ت添加 كلمات عامة مثل: تسجيل، موعد، نقل، جامعة، كلية، طالب
4. ركّز على التفاصيل المحددة في النص فقط

مثال على نص قصير ورد صحيح:
النص: "مواعيد التسجيل من 1 إلى 5 شوال"
الرد:
مواعيد التسجيل
1 إلى 5 شوال
متى يبدا التسجيل؟
متى ينتهي التسجيل؟

أعد كل سطر في سطر واحد بدون ترقيم أو عناوين."""


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
