import cloudinary
import cloudinary.uploader
import os
import logging
from bot.config import CLOUDINARY_URL

logger = logging.getLogger(__name__)

cloudinary.config(secure=True)


def upload_file(file_bytes: bytes, folder: str = "kku-bot") -> str:
    result = cloudinary.uploader.upload(file_bytes, folder=folder)
    return result["secure_url"]


def upload_image(file_bytes: bytes, folder: str = "kku-bot") -> str:
    result = cloudinary.uploader.upload(file_bytes, folder=folder, resource_type="image")
    return result["secure_url"]


def upload_raw(file_bytes: bytes, filename: str = "", folder: str = "kku-bot") -> str:
    result = cloudinary.uploader.upload(file_bytes, folder=folder, resource_type="raw")
    return result["secure_url"]


def download_raw(file_url: str) -> bytes | None:
    import urllib.parse
    import requests
    try:
        path = urllib.parse.urlparse(file_url).path
        path_decoded = urllib.parse.unquote(path)
        
        resource_type = "raw"
        upload_marker = "/raw/upload/"
        if upload_marker not in path_decoded:
            upload_marker = "/image/upload/"
            resource_type = "image"
            if upload_marker not in path_decoded:
                upload_marker = "/video/upload/"
                resource_type = "video"
                if upload_marker not in path_decoded:
                    logger.warning(f"download_raw: unknown URL format: {file_url}")
                    return None

        parts = path_decoded.split(upload_marker)
        if len(parts) != 2:
            return None
        path_after = parts[1]
        slash_idx = path_after.find("/")
        if slash_idx == -1:
            return None
        full_public_id = path_after[slash_idx + 1:]

        api_url = f"https://api.cloudinary.com/v1_1/kcjltbov/{resource_type}/download"
        resp = requests.get(
            api_url,
            params={"public_id": full_public_id, "type": "upload"},
            auth=("437369531767286", "GGV9VGXQac0LIJmDMfBkNwbLd9k"),
            timeout=90
        )
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception as e:
        print(f"Cloudinary download_raw exception: {e}")
        return None
