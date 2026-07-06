import os
import sys
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

# (plan_title_in_db, filename_on_disk)
MISSING_PLANS = [
    ("علم النفس ( اخصائي نفسي )", "علم النفس ( اخصائي نفسي ).pdf"),
    ("نظم المعلومات الإدارية", "نظم المعلومات الإدارية .pdf"),
    ("أصول الدين", "أصول الدين.pdf"),
    ("خطة الهندسة الكهربائية", "خطة الهندسة الكهربائية .pdf"),
    ("خطة الهندسة كيميائية", "خطة الهندسة كيميائية .pdf"),
    ("الإدارة المالية", "الإدارة المالية.pdf"),
    ("دبلوم إدارة أعمال", "دبلوم أدارة اعمال .pdf"),
]


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
    return True


def normalize_arabic(s: str) -> str:
    """Normalize Arabic text to NFC for reliable comparison."""
    return unicodedata.normalize("NFC", s)


def find_file_on_disk(filename: str) -> Path | None:
    """Find the file on disk, trying NFC normalization if exact match fails."""
    exact = UPLOADS_DIR / filename
    if exact.exists():
        return exact

    normalized_target = normalize_arabic(filename)
    for f in UPLOADS_DIR.iterdir():
        if f.suffix.lower() == ".pdf" and normalize_arabic(f.name) == normalized_target:
            return f

    return None


def upload_to_cloudinary(plan_title: str, file_path: Path) -> str | None:
    public_id = plan_title.replace(" ", "_")
    try:
        result = cloudinary.uploader.upload(
            str(file_path),
            folder="kku-bot/plans",
            resource_type="raw",
            public_id=public_id,
        )
        url = result.get("secure_url")
        logger.info(f"  Uploaded: {file_path.name} -> {url}")
        return url
    except Exception as e:
        logger.error(f"  Cloudinary upload failed: {e}")
        return None


async def main():
    configure_cloudinary()

    logger.info("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        success_count = 0
        fail_count = 0

        for plan_title, filename in MISSING_PLANS:
            logger.info(f"\n--- {plan_title} ---")

            # Find plan in DB
            row = await conn.fetchrow(
                "SELECT id, title, file_url FROM study_plans WHERE title = $1",
                plan_title,
            )
            if not row:
                logger.warning(f"  Plan NOT found in DB: '{plan_title}'")
                fail_count += 1
                continue

            plan_id = row["id"]
            current_url = row["file_url"]
            logger.info(f"  DB id={plan_id}, current file_url={current_url!r}")

            if current_url:
                logger.info("  Already has file_url, skipping upload")
                continue

            # Find file on disk
            file_path = find_file_on_disk(filename)
            if not file_path:
                logger.warning(f"  File NOT found on disk: {filename}")
                fail_count += 1
                continue

            # Upload to Cloudinary
            file_url = upload_to_cloudinary(plan_title, file_path)
            if not file_url:
                fail_count += 1
                continue

            # Update database
            await conn.execute(
                "UPDATE study_plans SET file_url = $1 WHERE id = $2",
                file_url,
                plan_id,
            )
            logger.info(f"  Updated DB: id={plan_id}")
            success_count += 1

        # Final verification
        logger.info("\n\n=== VERIFICATION ===")
        for plan_title, _ in MISSING_PLANS:
            row = await conn.fetchrow(
                "SELECT id, file_url FROM study_plans WHERE title = $1",
                plan_title,
            )
            if row:
                status = "OK" if row["file_url"] else "EMPTY"
                logger.info(f"  [{status}] {plan_title} -> {row['file_url']}")
            else:
                logger.info(f"  [NOT FOUND] {plan_title}")

        logger.info(f"\nDone! {success_count} uploaded, {fail_count} failed")

    finally:
        await conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
