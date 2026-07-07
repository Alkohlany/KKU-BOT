import cloudinary
import cloudinary.uploader
import os
from bot.config import CLOUDINARY_URL

cloudinary.config(secure=True)


def upload_file(file_bytes: bytes, folder: str = "kku-bot") -> str:
    result = cloudinary.uploader.upload(file_bytes, folder=folder)
    return result["secure_url"]


def upload_image(file_bytes: bytes, folder: str = "kku-bot") -> str:
    result = cloudinary.uploader.upload(file_bytes, folder=folder, resource_type="image")
    return result["secure_url"]


def upload_raw(file_bytes: bytes, filename: str, folder: str = "kku-bot") -> str:
    import re
    safe_name = re.sub(r'[^\w\s\u0600-\u06FF.\-]', '', filename)
    safe_name = safe_name.strip().replace(' ', '_')
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="raw",
    )
    return result["secure_url"]


def download_raw(file_url: str) -> bytes | None:
    import cloudinary.api
    import urllib.parse
    try:
        path = urllib.parse.urlparse(file_url).path
        parts = path.split("/raw/upload/")
        if len(parts) != 2:
            return None
        path_after = parts[1]
        slash_idx = path_after.find("/")
        if slash_idx == -1:
            return None
        full_public_id = path_after[slash_idx + 1:]
        ext_idx = full_public_id.rfind(".")
        public_id = full_public_id[:ext_idx] if ext_idx != -1 else full_public_id

        resource = cloudinary.api.resource(public_id, resource_type="raw")
        import requests
        resp = requests.get(resource["secure_url"], timeout=90)
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception as e:
        print(f"Cloudinary download_raw exception: {e}")
        return None
