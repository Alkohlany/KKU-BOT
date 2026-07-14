import boto3
import os
import uuid
import logging
import httpx
from bot.config import R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL

logger = logging.getLogger(__name__)

endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

def upload_file(file_bytes: bytes, folder: str = "kku-bot") -> str:
    ext = ".bin"
    key = f"{folder}/{uuid.uuid4().hex}{ext}"
    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=file_bytes)
    return f"{R2_PUBLIC_URL}/{key}"

def upload_image(file_bytes: bytes, folder: str = "kku-bot") -> str:
    key = f"{folder}/{uuid.uuid4().hex}.jpg"
    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=file_bytes, ContentType="image/jpeg")
    return f"{R2_PUBLIC_URL}/{key}"

def upload_raw(file_bytes: bytes, filename: str = "", folder: str = "kku-bot") -> str:
    if filename:
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        key = f"{folder}/{safe_name}"
    else:
        key = f"{folder}/{uuid.uuid4().hex}.bin"
    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=file_bytes)
    return f"{R2_PUBLIC_URL}/{key}"

def download_raw(file_url: str) -> bytes | None:
    try:
        resp = httpx.get(file_url, timeout=90)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        logger.error(f"Download failed: {e}")
    return None
