from fastapi import APIRouter
from bot.services.cloud_storage import list_all_folders, list_objects, delete_object

router = APIRouter()


@router.get("")
async def list_cloud_files(folder: str = None):
    if folder:
        return list_objects(folder)
    return list_all_folders()


@router.delete("")
async def delete_cloud_file(key: str):
    success = delete_object(key)
    if success:
        return {"message": "deleted"}
    return {"error": "failed"}
