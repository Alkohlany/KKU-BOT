import logging
from bot.config import NVIDIA_API_KEY

logger = logging.getLogger(__name__)

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODELS = [
    "meta/llama-3.2-1b-instruct",
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

    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    prompt = f"""أنت خبير في تحليل النصوص العربية واستخراج المعلومات الذكية.

مهمتك: تحليل النص التالي واستخراج بالضبط 5 كلمات مفتاحية و5 أسئلة ذكية.

---

## الكلمات المفتاحية (5 بالضبط):
- اختر كلمات تمثل الجوهر الحقيقي للموضوع
- كلمة واحدة فقط لكل مفتاح (مثلاً: تسجيل، موعد، انتقال)
- ركّز على الإجراءات والمفاهيم والمصطلحات المهمة
- اتجاهل الكلمات العامة: جامعة، كلية، طالب، عام، دليل، قروب، قناة، رابط
- اتجاهل الأسماء والسنوات إلا إذا كانت محور الموضوع
- لا تكرر أي كلمة

## الأسئلة (5 بالضبط):
- أسئلة طالب جامعي سعودي يسأ في قروب تيليجرام
- باللهجة السعودية البيضاء (وش، وين، كيف، متى، هل فيه، كم، أقدر، أبي أعرف)
- قصيرة ومباشرة بدون فصحى
- مرتبطة فقط بمحتوى النص (لا تؤلف معلومات)
- كل سؤال يبدأ بـ: وش، وين، كيف، متى، هل، كم، أقدر، أبي

---

النص:
{text}

---

التعليمات النهائية:
أعد بالضبط 10 أسطر فقط:
- الأسطر 1-5: الكلمات المفتاحية (كلمة في سطر)
- الأسطر 6-10: الأسئلة (سؤال في سطر)
- بدون ترقيم أو عناوين أو شرح
- بدون أي نص إضافي قبل أو بعد"""


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
