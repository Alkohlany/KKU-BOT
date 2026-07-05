from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from bot.api.config import ADMIN_USERNAME, ADMIN_PASSWORD
from bot.api.auth import create_access_token, get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if req.username != ADMIN_USERNAME or req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.username})
    return LoginResponse(token=token, username=req.username)


@router.post("/verify")
async def verify(user: dict = Depends(get_current_user)):
    return {"valid": True, "username": user.get("sub")}
