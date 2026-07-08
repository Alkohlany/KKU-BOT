from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_groups_redirect():
    return {"message": "Groups endpoint deprecated. Use /api/channels instead."}
