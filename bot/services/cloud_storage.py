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
    result = cloudinary.uploader.upload(file_bytes, folder=folder, resource_type="raw", public_id=filename)
    return result["secure_url"]
