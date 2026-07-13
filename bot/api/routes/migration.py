import asyncio
import uuid
import json
import httpx
import boto3
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, update as sa_update
from bot.api.auth import get_current_user
from bot.services.database import async_session
from bot.models.models import AutoResponse, News, Question, ScheduledPost, StudyPlan
from bot.config import R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL

router = APIRouter()

s3 = boto3.client("s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY)

def is_cloudinary_url(url):
    if not url:
        return False
    return "cloudinary" in url.lower() or "res.cloudinary.com" in url.lower()

def extract_from_json(files_json_str):
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

def get_ext(url):
    clean = url.split("?")[0].split("#")[0]
    parts = clean.rsplit(".", 1)
    return f".{parts[1]}" if len(parts) == 2 and len(parts[1]) <= 5 else ".bin"

@router.get("/cloudinary-urls")
async def list_cloudinary_urls(current_user: dict = Depends(get_current_user)):
    if current_user.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    async with async_session() as session:
        results = []
        tables = [
            (AutoResponse, ["file_url"], None),
            (News, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (Question, ["file_url"], None),
            (ScheduledPost, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (StudyPlan, ["plan_url", "file_url"], None),
        ]

        for model, cols, fjson_col in tables:
            result = await session.execute(select(model))
            for row in result.scalars().all():
                for col in cols:
                    val = getattr(row, col, None)
                    if val and is_cloudinary_url(val):
                        results.append({"table": model.__tablename__, "id": row.id, "col": col, "url": val})
                if fjson_col:
                    val = getattr(row, fjson_col, None)
                    if val:
                        for u in extract_from_json(val):
                            if is_cloudinary_url(u):
                                results.append({"table": model.__tablename__, "id": row.id, "col": fjson_col, "url": u})

        return {"total": len(results), "results": results}


@router.post("/migrate-from-cloudinary")
async def migrate_from_cloudinary(current_user: dict = Depends(get_current_user)):
    if current_user.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    async with async_session() as session:
        all_entries = []
        cloud_urls = []

        tables = [
            (AutoResponse, ["file_url"], None),
            (News, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (Question, ["file_url"], None),
            (ScheduledPost, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (StudyPlan, ["plan_url", "file_url"], None),
        ]

        for model, cols, fjson_col in tables:
            result = await session.execute(select(model))
            for row in result.scalars().all():
                entry = {"model": model, "id": row.id, "cols": {}, "files_json": None}
                for col in cols:
                    val = getattr(row, col, None)
                    if is_cloudinary_url(val):
                        entry["cols"][col] = val
                        cloud_urls.append(val)
                if fjson_col:
                    val = getattr(row, fjson_col, None)
                    if val:
                        for u in extract_from_json(val):
                            if is_cloudinary_url(u):
                                cloud_urls.append(u)
                                entry["files_json"] = val
                if entry["cols"] or entry["files_json"]:
                    all_entries.append(entry)

        unique_urls = list(dict.fromkeys(cloud_urls))
        if not unique_urls:
            return {"message": "No Cloudinary URLs found", "migrated": 0, "total": 0}

        url_map = {}
        async with httpx.AsyncClient(timeout=120) as client:
            for i, url in enumerate(unique_urls, 1):
                content = None
                for attempt in range(3):
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            content = resp.content
                            break
                    except Exception:
                        pass
                    await asyncio.sleep(2)
                if not content:
                    continue

                folder = "kku-bot/migrated"
                if "kku-bot/news" in url.lower():
                    folder = "kku-bot/news"
                elif "kku-bot/responses" in url.lower():
                    folder = "kku-bot/responses"
                elif "kku-bot/plans" in url.lower():
                    folder = "kku-bot/plans"

                key = f"{folder}/{uuid.uuid4().hex}{get_ext(url)}"
                try:
                    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=content)
                    url_map[url] = f"{R2_PUBLIC_URL}/{key}"
                except Exception:
                    continue

        updated = 0
        for entry in all_entries:
            model = entry["model"]
            row_id = entry["id"]
            updates = {}
            for col, old_url in entry["cols"].items():
                if old_url in url_map:
                    updates[col] = url_map[old_url]
            if entry["files_json"]:
                try:
                    items = json.loads(entry["files_json"])
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "url" in item and item["url"] in url_map:
                                item["url"] = url_map[item["url"]]
                    updates["files_json"] = json.dumps(items, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    pass
            if updates:
                stmt = sa_update(model).where(model.id == row_id).values(**updates)
                await session.execute(stmt)
                updated += 1

        await session.commit()

    return {
        "message": "Migration complete",
        "total": len(unique_urls),
        "migrated": len(url_map),
        "updated_records": updated
    }
