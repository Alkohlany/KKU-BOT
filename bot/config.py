import os
import re
import unicodedata
from dotenv import load_dotenv

load_dotenv()

ZERO_WIDTH = re.compile(r'[\u200b\u200c\u200d\ufeff\u00a0]')


def normalize_arabic(text):
    text = ZERO_WIDTH.sub('', text)
    text = unicodedata.normalize('NFKD', text)
    text = text.replace('ً', '').replace('ٌ', '').replace('ٍ', '')
    text = text.replace('َ', '').replace('ُ', '').replace('ِ', '').replace('ّ', '').replace('ْ', '')
    text = text.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('إ', 'ا').replace('أ', 'ا').replace('آ', 'ا')
    return text

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is not set. "
        "Please add your Telegram bot token on Railway."
    )

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please add a PostgreSQL database on Railway."
    )
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "kku-bot")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "")
OPENCODE_API_URL = os.getenv("OPENCODE_API_URL", "")
OPENCODE_AI_MODEL = os.getenv("OPENCODE_AI_MODEL", "")

