import asyncio
import os
import uuid
import json
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


@router.post("/migrate-local-files")
async def migrate_local_files(current_user: dict = Depends(get_current_user)):
    if current_user.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    url_map = {}
    uploaded = 0
    skipped = 0
    errors = []

    async with async_session() as session:
        tables = [
            (News, ["image_url", "file_url", "thumbnail_url"], "files_json"),
            (ScheduledPost, ["image_url", "file_url", "thumbnail_url"], "files_json"),
        ]

        for model, cols, fjson_col in tables:
            result = await session.execute(select(model))
            for row in result.scalars().all():
                for col in cols:
                    val = getattr(row, col, None)
                    if not val or not val.startswith("/app/"):
                        continue

                    local_path = val
                    if local_path in url_map:
                        continue

                    if not os.path.exists(local_path):
                        errors.append(f"{model.__tablename__} id={row.id}.{col}: file not found on server")
                        skipped += 1
                        continue

                    try:
                        with open(local_path, "rb") as f:
                            content = f.read()

                        folder = "kku-bot/migrated"
                        if "news" in local_path.lower():
                            folder = "kku-bot/news"
                        elif "scheduled" in local_path.lower():
                            folder = "kku-bot/scheduled"

                        ext = os.path.splitext(local_path)[1] or ".bin"
                        key = f"{folder}/{uuid.uuid4().hex}{ext}"
                        s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=content)
                        new_url = f"{R2_PUBLIC_URL}/{key}"
                        url_map[local_path] = new_url
                        uploaded += 1
                    except Exception as e:
                        errors.append(f"{model.__tablename__} id={row.id}.{col}: {str(e)}")

                if fjson_col:
                    val = getattr(row, fjson_col, None)
                    if not val:
                        continue
                    try:
                        items = json.loads(val)
                        changed = False
                        if isinstance(items, list):
                            for item in items:
                                if not isinstance(item, dict) or "url" not in item:
                                    continue
                                item_url = item["url"]
                                if not item_url or not item_url.startswith("/app/"):
                                    continue
                                if item_url in url_map:
                                    item["url"] = url_map[item_url]
                                    changed = True
                                    continue
                                if not os.path.exists(item_url):
                                    skipped += 1
                                    continue
                                try:
                                    with open(item_url, "rb") as f:
                                        content = f.read()
                                    folder = "kku-bot/news" if "news" in item_url.lower() else "kku-bot/scheduled"
                                    ext = os.path.splitext(item_url)[1] or ".bin"
                                    key = f"{folder}/{uuid.uuid4().hex}{ext}"
                                    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=content)
                                    new_url = f"{R2_PUBLIC_URL}/{key}"
                                    url_map[item_url] = new_url
                                    item["url"] = new_url
                                    uploaded += 1
                                except Exception as e:
                                    errors.append(f"files_json: {str(e)}")
                        if changed:
                            stmt = sa_update(model).where(model.id == row.id).values(files_json=json.dumps(items, ensure_ascii=False))
                            await session.execute(stmt)
                    except:
                        pass

        print("Updating database...")
        for model, cols, _ in tables:
            for col in cols:
                result = await session.execute(select(model))
                for row in result.scalars().all():
                    val = getattr(row, col, None)
                    if val and val in url_map:
                        stmt = sa_update(model).where(model.id == row.id).values(**{col: url_map[val]})
                        await session.execute(stmt)

        await session.commit()

    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "urls_mapped": len(url_map),
        "errors": errors
    }
