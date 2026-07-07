import google.genai as genai
from bot.config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)


def extract_keywords_and_questions(text: str, max_keywords: int = 5, max_questions: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    prompt = f"""اقرأ النص التالي واستخرج منه:
1. {max_keywords} كلمات مفتاحية أساسية تدل على موضوع النص (كلمة واحدة فقط لكل كلمة مفتاحية)
2. {max_questions} أسئلة متوقعة قد يسألها طلاب جامعيون عن هذا الموضوع

النص:
{text}

المطلوب: أعد النتيجة كقائمة فقط، كل عنصر في سطر جديد. الكلمات المفتاحية أولاً ثم الأسئلة.
لاتكتب أي شرح أو مقدمة."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        result = response.text.strip().split("\n")
        items = [line.strip("- ").strip() for line in result if line.strip()]
        return items
    except Exception as e:
        print(f"Gemini API error: {e}")
        return []
