import os
import sys
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
import asyncpg
import cloudinary
import cloudinary.uploader

load_dotenv()

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
    logger.warning("CLOUDINARY_URL not set. File uploads will be skipped.")

GROUPS = [
    (1, "\U0001f4c2خطط التخصصات لكلية اللغات والترجمة", "لغات"),
    (2, "\U0001f7e2خطط التخصصات الصحية 1447هـ", "صحي"),
    (3, "\U0001f4bbخطط كلية علوم الحاسب والمعلومات 1447هـ", "حاسب"),
    (4, "\U0001f4dcبرامج الدبلوم 1447هـ", "دبلوم"),
    (5, "\U0001f52cخطط كلية العلوم 1447هـ", "علوم"),
    (6, "\u262a\ufe0fخطط كلية الشريعة والدراسات الإسلامية 1447هـ", "شريعه"),
    (7, "\U0001f3d7\ufe0fخطط كلية الهندسة 1447هـ", "هندسه"),
    (8, "\U0001f4daخطط كلية التربية 1447هـ", "تربية"),
    (9, "\U0001f4bcخطط كلية الأعمال 1447هـ", "اعمال"),
    (10, "\U0001f4d6خطط كلية العلوم الإنسانية 1447هـ", "انسانيات"),
    (11, "\U0001f310خطط كلية اللغات والترجمة 1447هـ", "لغات2"),
    (12, "\U0001f3a8خطط كلية الثقافة والفنون 1447هـ", "فنون"),
    (13, "\u2708\ufe0fخطط كلية السياحة 1447هـ", "سياحه"),
]

PLANS = [
    # Group 1 - لغات
    (1, "خطة الترجمة", "خطة الترجمة.pdf"),
    (1, "خطة اللغة الإنجليزية", "خطة اللغة الإنجليزية.pdf"),

    # Group 2 - صحي
    (2, "التمريض", "التمريض.pdf"),
    (2, "الصيدلة", "الصيدلة.pdf"),
    (2, "الصحة العامة", "الصحة العامة.pdf"),
    (2, "العلاج الطبيعي", "العلاج الطبيعي.pdf"),
    (2, "علوم المختبرات الطبية", "علوم المختبرات الطبية.pdf"),
    (2, "طب وجراحة الفم و الاسنان", "طب وجراحة الفم و الاسنان.pdf"),
    (2, "تقنية التخدير", "تقنية التخدير.pdf"),
    (2, "تقنية الاشعة", "تقنية الاشعة.pdf"),
    (2, "تقنية الاسنان", "تقنية الاسنان.pdf"),
    (2, "علم السمع", "علم السمع.pdf"),
    (2, "امراض التخاطب", "امراض التخاطب.pdf"),
    (2, "علم النفس ( اخصائي نفسي )", "علم النفس ( اخصائي نفسي ).pdf"),
    (2, "السلامة والصحة المهنية ( دبلوم )", "السلامة والصحة المهنية ( دبلوم ).pdf"),

    # Group 3 - حاسب
    (3, "هندسة الحاسب", "هندسة الحاسب.pdf"),
    (3, "علوم حاسب", "علوم حاسب.pdf"),
    (3, "نظم معلومات", "نظم معلومات.pdf"),
    (3, "نظم المعلومات الإدارية", "نظم المعلومات الإدارية .pdf"),
    (3, "امن سيبراني", "امن سيبراني.pdf"),
    (3, "برمجة أنظمة المعلومات ( دبلوم )", "برمجة أنظمة المعلومات ( دبلوم ).pdf"),
    (3, "تطوير تطبيقات الويب والجوال (دبلوم)", "تطوير_تطبيقات_الويب_والجوال_دبلوم_.pdf"),
    (3, "تطبيقات الحاسب لفئة الصم ( دبلوم )", "تطبيقات الحاسب لفئة الصم ( دبلوم ).pdf"),
    (3, "خطه نظم المعلومات (دبلوم)", "خطه نظم المعلومات (دبلوم).pdf"),

    # Group 4 - دبلوم
    (4, "التسويق الإلكتروني ( دبلوم )", "التسويق الإلكتروني ( دبلوم ).pdf"),
    (4, "قانون الأعمال ( دبلوم )", "قانون الأعمال ( دبلوم ) .pdf"),
    (4, "المساعد القانوني ( دبلوم )", "المساعد القانوني ( دبلوم ).pdf"),
    (4, "الزراعة الذكية ( دبلوم )", "الزراعة الذكية ( دبلوم ).pdf"),
    (4, "تربية النحل ( دبلوم )", "تربية النحل ( دبلوم ).pdf"),

    # Group 5 - علوم
    (5, "خطة الرياضيات", "خطة الرياضيات.pdf"),
    (5, "خطة الفيزياء", "خطة الفيزياء.pdf"),
    (5, "خطة الكيمياء", "خطة الكيمياء.pdf"),
    (5, "خطة الاحياء", "خطة الاحياء.pdf"),
    (5, "خطة_الرياضيات_المالية_والعلوم_الاكتوارية", "خطة_الرياضيات_المالية_والعلوم_الاكتوارية.pdf"),

    # Group 6 - شريعة
    (6, "أصول الدين", "أصول الدين.pdf"),
    (6, "الشريعة", "الشريعه.pdf"),

    # Group 7 - هندسة
    (7, "خطة الهندسة المدنية", "خطة الهندسة المدنية.pdf"),
    (7, "خطة الهندسة الكهربائية", "خطة الهندسة الكهربائية .pdf"),
    (7, "خطة الهندسة الميكانيكية", "خطة الهندسة الميكانيكية .pdf"),
    (7, "خطة الهندسة الصناعية", "خطة الهندسة الصناعية.pdf"),
    (7, "خطة الهندسة كيميائية", "خطة الهندسة كيميائية .pdf"),
    (7, "خطة هندسة السلامة المهنية", "خطة هندسة السلامة المهنية.pdf"),

    # Group 8 - تربية
    (8, "الطفولة المبكرة", "الطفولة المبكرة.pdf"),

    # Group 9 - اعمال
    (9, "إدارة الأعمال", "ادارة الاعمال.pdf"),
    (9, "إدارة الموارد البشرية", "ادارة الموارد البشرية.pdf"),
    (9, "الإدارة المالية", "الإدارة المالية.pdf"),
    (9, "الاقتصاد", "الاقتصاد.pdf"),
    (9, "التسويق", "التسويق.pdf"),
    (9, "المحاسبة", "المحاسبة.pdf"),
    (9, "دبلوم محاسبة", "دبلوم محاسبة.pdf"),
    (9, "دبلوم إدارة أعمال", "دبلوم أدارة اعمال .pdf"),
    (9, "إدارة المشاريع السياحية والترفيهية (دبلوم)", "إدارة_المشاريع_السياحية_والترفيهية_دبلوم_.pdf"),

    # Group 10 - انسانيات
    (10, "اللغة العربية", "اللغة العربية.pdf"),
    (10, "التاريخ", "التاريخ.pdf"),
    (10, "الجغرافيا", "الجغرافيا.pdf"),
    (10, "القانون", "خطة القانون.pdf"),

    # Group 11 - لغات2
    (11, "خطة الطب والجراحة", "خطة الطب والجراحة.pdf"),

    # Group 12 - فنون
    (12, "العلوم الموسيقية", "العلوم الموسيقية .pdf"),
    (12, "العلاقات العامة والاتصال التسويقي", "العلاقات_العامة_والاتصال_التسويقي_.pdf"),
    (12, "علاقات عامة وإعلان", "علاقات عامة و اعلان.pdf"),
    (12, "الصحافة والتحرير الإلكتروني", "الصحافة و التحرير الالكتروني.pdf"),
    (12, "الصحافة والإعلام الرقمي", "الصحافة والاعلام الرقمي.pdf"),
    (12, "الإذاعة والتلفزيون والسينما", "الاذاعة والتلفزيون والسينما.pdf"),
    (12, "الإذاعة والتلفزيون", "الااذاعة و التلفزيون.pdf"),

    # Group 13 - سياحه
    (13, "فنون الطهي", "فنون الطهي.pdf"),
]


def configure_cloudinary():
    if not CLOUDINARY_URL:
        return False
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
        api_key=os.getenv("CLOUDINARY_API_KEY", ""),
        api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
        secure=True,
    )
    # Fallback: parse from CLOUDINARY_URL if individual vars not set
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


def upload_file_to_cloudinary(plan_title: str, filename: str) -> str | None:
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        logger.warning(f"File not found, skipping: {file_path}")
        return None

    public_id = plan_title.replace(" ", "_")
    try:
        result = cloudinary.uploader.upload(
            str(file_path),
            folder="kku-bot/plans",
            resource_type="raw",
            public_id=public_id,
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary upload failed for '{filename}': {e}")
        return None


async def seed_groups(conn: asyncpg.Connection) -> int:
    count = 0
    for group_id, title, group_tag in GROUPS:
        await conn.execute(
            """
            INSERT INTO study_plan_groups (id, title, group_tag, is_active, created_at)
            VALUES ($1, $2, $3, TRUE, NOW())
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                group_tag = EXCLUDED.group_tag
            """,
            group_id, title, group_tag,
        )
        count += 1
    logger.info(f"Upserted {count} study plan groups")
    return count


async def seed_plans(conn: asyncpg.Connection, upload_enabled: bool) -> tuple[int, int]:
    total = len(PLANS)
    uploaded = 0
    created = 0

    for idx, (group_id, plan_title, filename) in enumerate(PLANS, 1):
        logger.info(f"Uploading {idx}/{total}: {filename}")

        file_url = None
        if upload_enabled:
            file_url = upload_file_to_cloudinary(plan_title, filename)

        await conn.execute(
            """
            INSERT INTO study_plans (title, group_id, plan_url, file_url, is_active, created_at)
            VALUES ($1, $2, '', $3, TRUE, NOW())
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                group_id = EXCLUDED.group_id,
                file_url = EXCLUDED.file_url
            """,
            plan_title, group_id, file_url,
        )
        created += 1
        if file_url:
            uploaded += 1

    return created, uploaded


async def main():
    upload_enabled = configure_cloudinary()
    if not upload_enabled:
        logger.warning("Cloudinary not configured. Plans will be created without file URLs.")

    logger.info("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        logger.info("Seeding study plan groups...")
        groups_count = await seed_groups(conn)

        logger.info("Seeding study plans and uploading files...")
        plans_count, uploaded_count = await seed_plans(conn, upload_enabled)

        print(f"\nDone! Created {groups_count} groups, {plans_count} plans, {uploaded_count} files uploaded")
    finally:
        await conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
