import asyncio
import asyncpg
import os
import uuid
import json
import httpx
import boto3

DB_URL = "postgresql://kku_bot_user:DufoC9U0OtShdvhQ8qkIi29mfF6UrqF0@dpg-d955u9vavr4c739vcrqg-a.oregon-postgres.render.com/kku_bot"
R2_ACCOUNT_ID = "7f114137d67493306040c9aba1a3010b"
R2_ACCESS_KEY_ID = "e8b31da9213b528278ae296d37539afc"
R2_SECRET_ACCESS_KEY = "34ced3bca598d8445f216f6d0361970f1dee48638d20c71d2f7c2a291a17e4e4"
R2_BUCKET = "kku-bot"
R2_PUBLIC = "https://pub-d6f603d5fe754c03a6c8f7d10c4a0186.r2.dev"
CLOUDINARY_API_KEY = "437369531767286"
CLOUDINARY_API_SECRET = "GGV9VGXQac0LIJmDMfBkNwbLd9k"

s3 = boto3.client("s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY)

def is_cloudinary(url):
    return url and "cloudinary" in url.lower()

def is_local(url):
    return url and url.startswith("/app/")

def upload_to_r2(data, folder="kku-bot/migrated"):
    ext = ".bin"
    key = f"{folder}/{uuid.uuid4().hex}{ext}"
    s3.put_object(Bucket=R2_BUCKET, Key=key, Body=data)
    return f"{R2_PUBLIC}/{key}"

def get_ext(url):
    clean = url.split("?")[0].split("#")[0]
    parts = clean.rsplit(".", 1)
    return f".{parts[1]}" if len(parts) == 2 and len(parts[1]) <= 5 else ".bin"

def get_folder(url):
    lower = url.lower()
    if "news" in lower:
        return "kku-bot/news"
    if "responses" in lower:
        return "kku-bot/responses"
    if "plans" in lower:
        return "kku-bot/plans"
    if "scheduled" in lower:
        return "kku-bot/scheduled"
    return "kku-bot/migrated"

async def download_cloudinary(url):
    auth = httpx.BasicAuth(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, auth=auth)
                if resp.status_code == 200:
                    return resp.content
                print(f"  Attempt {attempt+1}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  Attempt {attempt+1}: {e}")
            await asyncio.sleep(2)
    return None

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        url_map = {}

        print("=== 1. Cloudinary files ===")
        tables = [
            ("auto_responses", ["file_url"]),
            ("news", ["image_url", "file_url", "thumbnail_url"]),
            ("questions", ["file_url"]),
            ("scheduled_posts", ["image_url", "file_url", "thumbnail_url"]),
            ("study_plans", ["plan_url", "file_url"]),
        ]

        cloud_urls = []
        for table, cols in tables:
            for col in cols:
                rows = await conn.fetch(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL")
                for r in rows:
                    if is_cloudinary(r[col]):
                        cloud_urls.append((table, r["id"], col, r[col]))

        print(f"Found {len(cloud_urls)} Cloudinary URLs")
        for table, row_id, col, url in cloud_urls:
            print(f"  {table} id={row_id}.{col}: {url}")
            if url in url_map:
                continue
            content = await download_cloudinary(url)
            if not content:
                print(f"  FAILED to download")
                continue
            folder = get_folder(url)
            ext = get_ext(url)
            key = f"{folder}/{uuid.uuid4().hex}{ext}"
            s3.put_object(Bucket=R2_BUCKET, Key=key, Body=content)
            new_url = f"{R2_PUBLIC}/{key}"
            url_map[url] = new_url
            print(f"  -> {new_url}")

        print("\n=== 2. Local server files ===")
        local_files = []
        for table, cols in tables:
            for col in cols:
                rows = await conn.fetch(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL")
                for r in rows:
                    if is_local(r[col]):
                        local_files.append((table, r["id"], col, r[col]))

        for table, row_id, col, url in local_files:
            print(f"  {table} id={row_id}.{col}: {url}")
            if url in url_map:
                continue
            local_path = url
            if not os.path.exists(local_path):
                print(f"  NOT FOUND locally (on Render server)")
                continue
            with open(local_path, "rb") as f:
                content = f.read()
            folder = get_folder(url)
            ext = get_ext(url)
            key = f"{folder}/{uuid.uuid4().hex}{ext}"
            s3.put_object(Bucket=R2_BUCKET, Key=key, Body=content)
            new_url = f"{R2_PUBLIC}/{key}"
            url_map[url] = new_url
            print(f"  -> {new_url}")

        print(f"\n=== 3. Updating database ({len(url_map)} URLs mapped) ===")
        updated = 0
        for table, cols in tables:
            for col in cols:
                rows = await conn.fetch(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL")
                for r in rows:
                    if r[col] in url_map:
                        await conn.execute(f"UPDATE {table} SET {col} = $1 WHERE id = $2", url_map[r[col]], r["id"])
                        updated += 1

        for table in ["news", "scheduled_posts"]:
            rows = await conn.fetch(f"SELECT id, files_json FROM {table} WHERE files_json IS NOT NULL")
            for r in rows:
                if not r["files_json"]:
                    continue
                try:
                    items = json.loads(r["files_json"])
                    changed = False
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "url" in item and item["url"] in url_map:
                                item["url"] = url_map[item["url"]]
                                changed = True
                    if changed:
                        await conn.execute(f"UPDATE {table} SET files_json = $1 WHERE id = $2", json.dumps(items, ensure_ascii=False), r["id"])
                        updated += 1
                except:
                    pass

        print(f"Updated {updated} records")
        print("\nDone!")
    finally:
        await conn.close()

asyncio.run(main())
