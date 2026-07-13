import os
import sys
import unicodedata
import difflib
import uuid
from pathlib import Path

import psycopg2
import boto3

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("FATAL: DATABASE_URL not set")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
            new_url = upload_file(file_bytes, file_path.name)
        except Exception as e:
            print(f"  !! Upload failed: {e}")
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
