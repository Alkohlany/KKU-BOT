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

    prompt = f"""
أنت متخصص في فهم النصوص العربية واستخراج المعلومات المهمة.

مهمتك هي تحليل النص واستخراج أهم المعلومات، وليس اختيار أكثر الكلمات تكرارًا.

استخرج من النص:

1. {max_keywords} كلمة مفتاحية تمثل الفكرة أو الموضوع الحقيقي للنص.
2. {max_questions} أسئلة متوقعة قد يطرحها طالب جامعي سعودي حول محتوى النص.

### قواعد استخراج الكلمات المفتاحية:
- اختر كلمات تعبر عن المعنى الأساسي للنص.
- كلمة واحدة فقط لكل كلمة مفتاحية.
- لا تعتمد على تكرار الكلمة، بل على أهميتها في فهم الموضوع.
- تجاهل الكلمات العامة أو الشائعة أو التي لا تضيف معنى، مثل:
  جامعة، كلية، طالب، عام، دليل، قروب، قناة، رابط، تيليجرام، واتساب، الملك، خالد، السعودية، سنة، 1447...
- تجاهل أسماء الأشخاص والجامعات والجهات إلا إذا كانت هي محور النص نفسه.
- تجاهل الكلمات الموجودة فقط في العناوين أو الهاشتاقات أو الروابط أو النصوص المكررة.
- أعطِ الأولوية للمفاهيم، والتخصصات، والإجراءات، والأنظمة، والمصطلحات المهمة.
- لا تكرر أي كلمة مفتاحية.
- إذا كان النص لا يحتوي على كلمات مهمة كافية، فأعد عددًا أقل من المطلوب بدلاً من إضافة كلمات ضعيفة أو غير مفيدة.

### قواعد إنشاء الأسئلة:
- اجعل جميع الأسئلة مرتبطة مباشرة بمحتوى النص.
- لا تؤلف معلومات غير موجودة أو لا يمكن استنتاجها منطقيًا من النص.
- اكتب الأسئلة باللهجة السعودية البيضاء (المفهومة في جميع مناطق المملكة).
- اكتبها كما لو أنها مرسلة من طالب جامعي سعودي في مجموعة تيليجرام أو واتساب.
- استخدم أسلوبًا طبيعيًا وغير رسمي مثل:
  وش، وين، كيف، متى، هل فيه، كم، أقدر، أبي أعرف...
- تجنب الفصحى الرسمية مثل:
  "ما الذي"، "كيف يمكنني"، "أين يمكنني".
- اجعل الأسئلة قصيرة وواضحة.
- لا تكرر نفس الفكرة بصيغ مختلفة.

النص:
{text}

أعد النتيجة فقط بهذا الترتيب:
- الكلمات المفتاحية أولاً.
- ثم الأسئلة.
- كل عنصر في سطر مستقل.
- بدون ترقيم.
- بدون عناوين.
- بدون أي شرح أو مقدمة أو خاتمة.
"""

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
