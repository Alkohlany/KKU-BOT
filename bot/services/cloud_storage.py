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

def upload_raw_streaming(file_obj, filename: str = "", folder: str = "kku-bot", content_type: str = None) -> str:
    """Upload large files using streaming to avoid loading entire file into memory."""
    if filename:
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        key = f"{folder}/{safe_name}"
    else:
        key = f"{folder}/{uuid.uuid4().hex}.bin"

    kwargs = {"Bucket": R2_BUCKET_NAME, "Key": key, "Body": file_obj}
    if content_type:
        kwargs["ContentType"] = content_type

    s3.put_object(**kwargs)
    return f"{R2_PUBLIC_URL}/{key}"

def download_raw(file_url: str) -> bytes | None:
    try:
        resp = httpx.get(file_url, timeout=90)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        logger.error(f"Download failed: {e}")
    return None


def list_objects(folder="kku-bot"):
    try:
        result = s3.list_objects_v2(Bucket=R2_BUCKET_NAME, Prefix=folder + "/")
        files = []
        for obj in result.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            name = key.split("/")[-1]
            files.append({
                "key": key,
                "url": R2_PUBLIC_URL + "/" + key,
                "name": name,
                "size": obj["Size"],
                "folder": folder,
            })
        return files
    except Exception as e:
        logger.error("List objects failed: %s", e)
        return []


def find_file_by_name(filename, folder="kku-bot"):
    files = list_objects(folder)
    for f in files:
        if f["name"] == filename:
            return f["url"]
    return None


def find_file_by_content(file_bytes: bytes, folder="kku-bot", max_size=10*1024*1024):
    if len(file_bytes) > max_size:
        return None
    import hashlib
    file_hash = hashlib.md5(file_bytes).hexdigest()
    files = list_objects(folder)
    for f in files:
        existing = download_raw(f["url"])
        if existing and hashlib.md5(existing).hexdigest() == file_hash:
            return f["url"]
    return None


def list_all_folders():
    folders = {}
    for folder in ["kku-bot/news", "kku-bot/plans", "kku-bot/scheduled"]:
        files = list_objects(folder)
        if files:
            folders[folder] = files
    return folders


def list_all_folders_recursive():
    try:
        result = s3.list_objects_v2(Bucket=R2_BUCKET_NAME, Prefix="kku-bot/", Delimiter="/")
        folders = {}
        root_files = []
        for prefix in result.get("CommonPrefixes", []):
            folder_path = prefix["Prefix"].rstrip("/")
            folders[folder_path] = {
                "files": list_objects(folder_path),
                "subfolders": list_subfolders(folder_path),
            }
        for obj in result.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            name = key.split("/")[-1]
            root_files.append({
                "key": key,
                "url": R2_PUBLIC_URL + "/" + key,
                "name": name,
                "size": obj["Size"],
                "folder": "kku-bot",
            })
        folders["kku-bot"] = {
            "files": root_files,
            "subfolders": [{"path": p["Prefix"].rstrip("/"), "name": p["Prefix"].rstrip("/").split("/")[-1]} for p in result.get("CommonPrefixes", [])],
        }
        return folders
    except Exception as e:
        logger.error("List all folders recursive failed: %s", e)
        return {"kku-bot": {"files": [], "subfolders": []}}


def list_subfolders(folder="kku-bot"):
    try:
        result = s3.list_objects_v2(Bucket=R2_BUCKET_NAME, Prefix=folder + "/", Delimiter="/")
        subfolders = []
        for prefix in result.get("CommonPrefixes", []):
            path = prefix["Prefix"].rstrip("/")
            name = path.split("/")[-1]
            subfolders.append({"path": path, "name": name})
        return subfolders
    except Exception as e:
        logger.error("List subfolders failed: %s", e)
        return []


def create_folder(folder_path):
    try:
        key = folder_path.rstrip("/") + "/"
        s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=b"")
        return True
    except Exception as e:
        logger.error("Create folder failed: %s", e)
        return False


def delete_folder(prefix):
    try:
        prefix = prefix.rstrip("/") + "/"
        paginator = s3.get_paginator("list_objects_v2")
        to_delete = []
        for page in paginator.paginate(Bucket=R2_BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                to_delete.append({"Key": obj["Key"]})
        if not to_delete:
            return True
        for i in range(0, len(to_delete), 1000):
            s3.delete_objects(
                Bucket=R2_BUCKET_NAME,
                Delete={"Objects": to_delete[i:i+1000]}
            )
        return True
    except Exception as e:
        logger.error("Delete folder failed: %s", e)
        return False


def rename_object(old_key, new_key):
    try:
        s3.copy_object(
            Bucket=R2_BUCKET_NAME,
            CopySource={"Bucket": R2_BUCKET_NAME, "Key": old_key},
            Key=new_key,
        )
        s3.delete_object(Bucket=R2_BUCKET_NAME, Key=old_key)
        return True
    except Exception as e:
        logger.error("Rename object failed: %s", e)
        return False


def move_object(old_key, new_folder):
    try:
        name = old_key.split("/")[-1]
        new_key = new_folder.rstrip("/") + "/" + name
        if old_key == new_key:
            return True
        s3.copy_object(
            Bucket=R2_BUCKET_NAME,
            CopySource={"Bucket": R2_BUCKET_NAME, "Key": old_key},
            Key=new_key,
        )
        s3.delete_object(Bucket=R2_BUCKET_NAME, Key=old_key)
        return True
    except Exception as e:
        logger.error("Move object failed: %s", e)
        return False


def delete_object(key):
    try:
        s3.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
        return True
    except Exception as e:
        logger.error("Delete object failed: %s", e)
        return False
