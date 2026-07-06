import os
import sys
import unicodedata
import difflib
from pathlib import Path

import psycopg2
import cloudinary
import cloudinary.uploader

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("FATAL: DATABASE_URL not set")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")
if not CLOUDINARY_URL:
    print("FATAL: CLOUDINARY_URL not set")
    sys.exit(1)

cloudinary.config(
    cloud_name="kcjltbov",
    api_key="437369531767286",
    api_secret="GGV9VGXQac0LIJmDMfBkNwbLd9k",
    secure=True,
)

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u200f", "").replace("\u200e", "")
    s = s.replace("(", "").replace(")", "").replace("(", "").replace(")", "")
    s = s.strip()
    return s


def normalize_for_compare(s: str) -> str:
    s = normalize(s)
    s = s.replace(" ", "").replace("_", "").replace("-", "")
    return s


def find_best_match(title: str, pdf_files: list[Path]) -> Path | None:
    title_norm = normalize(title)
    title_compact = normalize_for_compare(title)

    for f in pdf_files:
        stem_norm = normalize(f.stem)
        if normalize_for_compare(stem_norm) == title_compact:
            return f

    candidates = []
    for f in pdf_files:
        stem_norm = normalize(f.stem)
        ratio = difflib.SequenceMatcher(None, title_compact, normalize_for_compare(stem_norm)).ratio()
        candidates.append((ratio, f))
    candidates.sort(key=lambda x: -x[0])
    if candidates and candidates[0][0] >= 0.6:
        return candidates[0][1]
    return None


def main():
    pdf_files = sorted([f for f in UPLOADS_DIR.iterdir() if f.suffix.lower() == ".pdf"])
    print(f"Found {len(pdf_files)} PDF files in uploads/\n")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, title, file_url FROM study_plans ORDER BY id")
    plans = cur.fetchall()
    print(f"Found {len(plans)} plans in database\n")

    success = 0
    fail = 0
    unmatched = []

    for i, (plan_id, title, current_url) in enumerate(plans, 1):
        print(f"[{i}/{len(plans)}] (id={plan_id}) {title}")

        file_path = find_best_match(title, pdf_files)
        if not file_path:
            print(f"  !! NO MATCHING FILE FOUND")
            unmatched.append((plan_id, title))
            continue

        print(f"  -> Matched file: {file_path.name}")

        try:
            file_bytes = file_path.read_bytes()
        except Exception as e:
            print(f"  !! Read failed: {e}")
            fail += 1
            continue

        print(f"  Uploading ({len(file_bytes)} bytes)...")
        try:
            result = cloudinary.uploader.upload(
                file_bytes,
                folder="kku-bot/plans",
                resource_type="raw",
                access_control=[{"access_type": "anonymous"}],
            )
        except Exception as e:
            print(f"  !! Upload failed: {e}")
            fail += 1
            continue

        new_url = result.get("secure_url")
        if not new_url:
            print(f"  !! No secure_url in response")
            fail += 1
            continue

        cur.execute(
            "UPDATE study_plans SET file_url = %s WHERE id = %s",
            (new_url, plan_id),
        )
        conn.commit()
        print(f"  OK -> {new_url}")
        success += 1

    print(f"\n=== DONE ===")
    print(f"Success: {success}")
    print(f"Failed:  {fail}")
    print(f"Unmatched: {len(unmatched)}")
    for pid, title in unmatched:
        print(f"  id={pid}: {title}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
