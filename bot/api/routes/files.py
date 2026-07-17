from fastapi import APIRouter, UploadFile, File, Form
from bot.services.cloud_storage import (
    list_all_folders, list_objects, delete_object,
    list_all_folders_recursive, list_subfolders,
    create_folder, delete_folder, rename_object, move_object,
    upload_raw,
)

router = APIRouter()


@router.get("")
async def list_cloud_files(folder: str = None):
    if folder:
        files = list_objects(folder)
        subfolders = list_subfolders(folder)
        return {"files": files, "subfolders": subfolders}
    return list_all_folders_recursive()


@router.post("")
async def upload_cloud_file(
    file: UploadFile = File(...),
    folder: str = Form("kku-bot"),
):
    content = await file.read()
    url = upload_raw(content, file.filename, folder)
    return {"url": url, "name": file.filename, "folder": folder}


@router.delete("")
async def delete_cloud_file(key: str):
    success = delete_object(key)
    if success:
        return {"message": "deleted"}
    return {"error": "failed"}


@router.put("/rename")
async def rename_cloud_file(old_key: str = Form(...), new_name: str = Form(...)):
    parts = old_key.rsplit("/", 1)
    if len(parts) == 2:
        new_key = parts[0] + "/" + new_name
    else:
        new_key = new_name
    success = rename_object(old_key, new_key)
    if success:
        return {"message": "renamed", "new_key": new_key}
    return {"error": "failed"}


@router.put("/move")
async def move_cloud_file(key: str = Form(...), new_folder: str = Form(...)):
    success = move_object(key, new_folder)
    if success:
        return {"message": "moved"}
    return {"error": "failed"}


@router.post("/folder")
async def create_cloud_folder(path: str = Form(...)):
    success = create_folder(path)
    if success:
        return {"message": "created", "path": path}
    return {"error": "failed"}


@router.delete("/folder")
async def delete_cloud_folder(path: str):
    success = delete_folder(path)
    if success:
        return {"message": "deleted", "path": path}
    return {"error": "failed"}
