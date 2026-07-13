import asyncio
import os
import uuid
import json
import httpx
import boto3
import dotenv

dotenv.load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(__file__))

from bot.services.database import async_session
from bot.models.models import AutoResponse, News, Question, ScheduledPost, StudyPlan
from sqlalchemy import select, update as sa_update
from bot.config import R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL

s3 = boto3.client("s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY)

def is_cloudinary_url(url):
    if not url:
        return False
    return "cloudinary" in url.lower() or "res.cloudinary.com" in url.lower()

def extract_urls_from_files_json(files_json_str):
    urls = []
    if not files_json_str:
        return urls
    try:
        items = json.loads(files_json_str)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "url" in item:
                    urls.append(item["url"])
    except (json.JSONDecodeError, TypeError):
        pass
    return urls

def get_ext_from_url(url):
    clean = url.split("?")[0].split("#")[0]
    parts = clean.rsplit(".", 1)
    if len(parts) == 2 and len(parts[1]) <= 5:
        return f".{parts[1]}"
    return ".bin"

def upload_to_r2(file_bytes, key):
    try:
        s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=file_bytes)
        return True
    except Exception as e:
        print(f"  R2 upload failed: {e}")
        return False

def rebuild_files_json(files_json_str, url_map):
    if not files_json_str:
        return files_json_str
    try:
        items = json.loads(files_json_str)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "url" in item and item["url"] in url_map:
                    item["url"] = url_map[item["url"]]
        return json.dumps(items, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return files_json_str

async def main():
    print("Starting Cloudinary to R2 migration...\n")

    async with async_session() as session:
        all_entries = []
        cloudinary_urls = []

        tables = [
            (AutoResponse, ["file_url"], None),
            (News, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (Question, ["file_url"], None),
            (ScheduledPost, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (StudyPlan, ["plan_url", "file_url"], None),
        ]

        for model, cols, files_json_col in tables:
            result = await session.execute(select(model))
            rows = result.scalars().all()
            for row in rows:
                entry = {"model": model, "id": row.id, "cols": {}, "files_json": None}
                for col in cols:
                    val = getattr(row, col, None)
                    if is_cloudinary_url(val):
                        entry["cols"][col] = val
                        cloudinary_urls.append(val)
                if files_json_col:
                    val = getattr(row, files_json_col, None)
                    if val:
                        urls = extract_urls_from_files_json(val)
                        cloud_urls = [u for u in urls if is_cloudinary_url(u)]
                        if cloud_urls:
                            entry["files_json"] = val
                            cloudinary_urls.extend(cloud_urls)
                if entry["cols"] or entry["files_json"]:
                    all_entries.append(entry)

        unique_urls = list(dict.fromkeys(cloudinary_urls))
        print(f"Found {len(unique_urls)} unique Cloudinary URLs in {len(all_entries)} records\n")

        if not unique_urls:
            print("No Cloudinary URLs found. Nothing to do.")
            return

        url_map = {}
        for i, url in enumerate(unique_urls, 1):
            print(f"[{i}/{len(unique_urls)}] Downloading...")
            content = None
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=120) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            content = resp.content
                            break
                except Exception as e:
                    print(f"  Attempt {attempt+1} error: {e}")
                await asyncio.sleep(2)
            if not content:
                print(f"  SKIP: download failed")
                continue

            folder = "kku-bot/migrated"
            if "kku-bot/news" in url.lower():
                folder = "kku-bot/news"
            elif "kku-bot/responses" in url.lower():
                folder = "kku-bot/responses"
            elif "kku-bot/plans" in url.lower():
                folder = "kku-bot/plans"

            ext = get_ext_from_url(url)
            key = f"{folder}/{uuid.uuid4().hex}{ext}"
            if not upload_to_r2(content, key):
                print(f"  SKIP: upload failed")
                continue

            new_url = f"{R2_PUBLIC_URL}/{key}"
            url_map[url] = new_url
            print(f"  -> {new_url}")

        print(f"\nMigrated {len(url_map)}/{len(unique_urls)} files")

        if not url_map:
            return

        print("\nUpdating database...")
        updated = 0
        for entry in all_entries:
            model = entry["model"]
            row_id = entry["id"]
            updates = {}
            for col, old_url in entry["cols"].items():
                if old_url in url_map:
                    updates[col] = url_map[old_url]
            if entry["files_json"]:
                rebuilt = rebuild_files_json(entry["files_json"], url_map)
                if rebuilt != entry["files_json"]:
                    updates["files_json"] = rebuilt
            if updates:
                stmt = sa_update(model).where(model.id == row_id).values(**updates)
                await session.execute(stmt)
                updated += 1

        await session.commit()
        print(f"Updated {updated} records")
        print("\nMigration complete!")

if __name__ == "__main__":
    asyncio.run(main())
