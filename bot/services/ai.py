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

    prompt = f"""أنت طالب جامعي سعودي تساعد زملاءك في قروب تيليجرام.

حلل النص التالي وأعد 5 ردود فقط (كلمات مفتاحية + أسئلة باللهجة السعودية):

النص:
{text}

---

القواعد:
1. أعد بالضبط 5 أسطر فقط
2. كل سطر رد واحد (كلمة مفتاحية أو سؤال)
3. الأسئلة باللهجة السعودية البيضاء только

أمثلة على أسئلة سعودية صحيحة:
- وش أحسن وقت للتسجيل؟
- وين أقدر أسجل؟
- كيف أحوال التحويل؟
- متى آخر موعد؟
- هل فيه نقل داخلي؟
- كم המקسم؟
- أبي أعرف إجراءات التسجيل
- أقدر أسجل أونلاين؟

4. الكلمات المفتاحية تكون كلمة واحدة مثل: تسجيل، موعد، نقل، تحويل، انصراف
5. لا تكتب فصحى مثل "ما الذي" أو "كيف يمكنني"
6. لا تكتب ترقيم أو عناوين
7. لا تكتب أي شرح قبل أو بعد"""


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
