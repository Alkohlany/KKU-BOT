import os
import sys
import asyncio
import logging
import unicodedata
import uuid
from pathlib import Path

import asyncpg
import boto3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    logger.error("DATABASE_URL not set. Exiting.")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "7f114137d67493306040c9aba1a3010b")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "e8b31da9213b528278ae296d37539afc")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "34ced3bca598d8445f216f6d0361970f1dee48638d20c71d2f7c2a291a17e4e4")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "kku-bot")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://pub-d6f603d5fe754c03a6c8f7d10c4a0186.r2.dev")

s3 = boto3.client("s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY)

def upload_file(data, filename, folder="kku-bot/plans"):
    ext = os.path.splitext(filename)[1]
    key = f"{folder}/{uuid.uuid4().hex}{ext}"
    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=data)
    return f"{R2_PUBLIC_URL}/{key}"


def normalize_arabic(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def find_file_on_disk(filename: str) -> Path | None:
    exact = UPLOADS_DIR / filename
    if exact.exists():
        return exact
    normalized = normalize_arabic(filename)
    for f in UPLOADS_DIR.iterdir():
        if f.suffix.lower() == ".pdf" and normalize_arabic(f.name) == normalized:
            return f
    return None


def build_expected_filename(plan_title: str) -> str:
    return f"{plan_title}.pdf"


def reupload(file_bytes: bytes, plan_title: str) -> str | None:
    filename = f"{plan_title}.pdf"
    try:
        return upload_file(file_bytes, filename)
    except Exception as e:
        logger.error(f"  Upload failed: {e}")
        return None


async def main():
    logger.info("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            "SELECT id, title, file_url FROM study_plans ORDER BY id"
        )
        logger.info(f"Found {len(rows)} plans in database.")

        success = 0
        fail = 0
        skip_no_file = 0

        for i, row in enumerate(rows, 1):
            plan_id = row["id"]
            title = row["title"]

            expected_filename = build_expected_filename(title)
            file_path = find_file_on_disk(expected_filename)

            if not file_path:
                logger.warning(f"[{i}/{len(rows)}] {title} - file not found on disk: {expected_filename}")
                skip_no_file += 1
                continue

            logger.info(f"[{i}/{len(rows)}] {title} - uploading from {file_path.name}")

            try:
                file_bytes = file_path.read_bytes()
            except Exception as e:
                logger.error(f"  Read failed: {e}")
                fail += 1
                continue

            new_url = reupload(file_bytes, title)
            if not new_url:
                fail += 1
                continue

            await conn.execute(
                "UPDATE study_plans SET file_url = $1 WHERE id = $2",
                new_url,
                plan_id,
            )
            logger.info(f"  New URL: {new_url}")
            success += 1

        logger.info(f"\nDone! {success} re-uploaded, {fail} failed, {skip_no_file} skipped (no local file).")

    finally:
        await conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
