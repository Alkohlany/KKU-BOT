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
CLOUD_NAME = "kcjltbov"
CLOUDINARY_API_KEY = "437369531767286"
CLOUDINARY_API_SECRET = "GGV9VGXQac0LIJmDMfBkNwbLd9k"

s3 = boto3.client("s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY)

async def download_cloudinary_raw(url):
    """Try downloading via Cloudinary Admin API"""
    public_id = url.split("/upload/")[-1] if "/upload/" in url else None
    if not public_id:
        return None
    public_id = public_id.rsplit(".", 1)[0]
    auth = httpx.BasicAuth(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
    api_url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/raw/download"
    async with httpx.AsyncClient(timeout=120) as client:
        for attempt in range(3):
            try:
                resp = await client.get(api_url, params={"public_id": public_id, "type": "upload"}, auth=auth)
                if resp.status_code == 200:
                    return resp.content
                print(f"  API attempt {attempt+1}: HTTP {resp.status_code} - {resp.text[:200]}")
            except Exception as e:
                print(f"  API attempt {attempt+1}: {e}")
            await asyncio.sleep(2)
    return None

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        url_map = {}
        print("=== Cloudinary migration ===")

        rows = await conn.fetch("""
            SELECT 'auto_responses' as tbl, id, file_url as url, 'file_url' as col FROM auto_responses WHERE file_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'news', id, file_url, 'file_url' FROM news WHERE file_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'questions', id, file_url, 'file_url' FROM questions WHERE file_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'scheduled_posts', id, image_url, 'image_url' FROM scheduled_posts WHERE image_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'scheduled_posts', id, file_url, 'file_url' FROM scheduled_posts WHERE file_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'scheduled_posts', id, thumbnail_url, 'thumbnail_url' FROM scheduled_posts WHERE thumbnail_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'study_plans', id, plan_url, 'plan_url' FROM study_plans WHERE plan_url LIKE '%cloudinary%'
            UNION ALL
            SELECT 'study_plans', id, file_url, 'file_url' FROM study_plans WHERE file_url LIKE '%cloudinary%'
        """)

        print(f"Found {len(rows)} Cloudinary URLs")
        for r in rows:
            url = r["url"]
            print(f"\n  {r['tbl']} id={r['id']}.{r['col']}: {url}")
            if url in url_map:
                print(f"  Already mapped")
                continue
            content = await download_cloudinary_raw(url)
            if not content:
                print(f"  FAILED")
                continue
            ext = f".{url.split('.')[-1].split('?')[0]}" if '.' in url.split('/')[-1] else ".bin"
            key = f"kku-bot/plans/{uuid.uuid4().hex}{ext}"
            s3.put_object(Bucket=R2_BUCKET, Key=key, Body=content)
            new_url = f"{R2_PUBLIC}/{key}"
            url_map[url] = new_url
            print(f"  OK -> {new_url}")

        print(f"\n=== Updating database ({len(url_map)} mapped) ===")
        updated = 0
        for table in ["auto_responses", "news", "questions", "scheduled_posts", "study_plans"]:
            for col in ["file_url", "image_url", "thumbnail_url", "plan_url"]:
                rows2 = await conn.fetch(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} LIKE '%cloudinary%'")
                for r2 in rows2:
                    if r2[col] in url_map:
                        await conn.execute(f"UPDATE {table} SET {col} = $1 WHERE id = $2", url_map[r2[col]], r2["id"])
                        updated += 1
                        print(f"  Updated {table} id={r2['id']}.{col}")

        print(f"\nTotal updated: {updated}")
    finally:
        await conn.close()

asyncio.run(main())
