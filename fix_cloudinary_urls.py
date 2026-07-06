import os
import sys
import re
import asyncio
import logging
import unicodedata
from pathlib import Path

import asyncpg
import cloudinary
import cloudinary.uploader

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

CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")
if not CLOUDINARY_URL:
    logger.error("CLOUDINARY_URL not set. Exiting.")
    sys.exit(1)


def configure_cloudinary():
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
        api_key=os.getenv("CLOUDINARY_API_KEY", ""),
        api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
        secure=True,
    )
    if not cloudinary.config().cloud_name and CLOUDINARY_URL.startswith("cloudinary://"):
        parts = CLOUDINARY_URL.replace("cloudinary://", "").split("@")
        if len(parts) == 2:
            api_key_secret = parts[0].split(":")
            if len(api_key_secret) == 2:
                cloudinary.config(
                    cloud_name=parts[1],
                    api_key=api_key_secret[0],
                    api_secret=api_key_secret[1],
                    secure=True,
                )


def sanitize_title(title: str) -> str:
    safe = re.sub(r'[^\w\s\u0600-\u06FF]', '', title)
    safe = safe.replace(' ', '_')
    return safe


def find_file_on_disk(plan_title: str) -> Path | None:
    title_nfc = unicodedata.normalize('NFC', plan_title)
    expected_name = f"{title_nfc}.pdf"
    exact = UPLOADS_DIR / expected_name
    if exact.exists():
        return exact
    for f in UPLOADS_DIR.iterdir():
        if f.suffix.lower() != ".pdf":
            continue
        fname_nfc = unicodedata.normalize('NFC', f.stem)
        if fname_nfc == title_nfc:
            return f
    return None


def reupload(file_bytes: bytes, plan_title: str) -> str | None:
    public_id = sanitize_title(plan_title)
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder="kku-bot/plans",
            resource_type="raw",
            public_id=public_id,
            access_control=[{"access_type": "anonymous"}],
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"  Upload failed: {e}")
        return None


async def main():
    configure_cloudinary()
    logger.info("Configured Cloudinary.")

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
        skip_ok = 0

        for i, row in enumerate(rows, 1):
            plan_id = row["id"]
            title = row["title"]
            current_url = row["file_url"]

            logger.info(f"[{i}/{len(rows)}] (id={plan_id}) {title}")

            file_path = find_file_on_disk(title)

            if not file_path:
                logger.warning(f"  File not found on disk for: {title}")
                skip_no_file += 1
                continue

            # If it already has a clean URL (no double-encoding), skip
            if current_url and '%25' not in current_url:
                logger.info(f"  URL already clean, skipping")
                skip_ok += 1
                continue

            logger.info(f"  Uploading from {file_path.name}")

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
            logger.info(f"  Updated: {new_url}")
            success += 1

        logger.info(f"\nDone! {success} re-uploaded, {fail} failed, {skip_no_file} skipped (no file), {skip_ok} skipped (already clean).")

    finally:
        await conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
