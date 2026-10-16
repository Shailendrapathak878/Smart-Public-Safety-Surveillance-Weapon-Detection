from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from config import settings
from auth.authentication import verify_password, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    message: str

# Simple mock token for prototype
MOCK_TOKEN = "prototype_token_123"

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    if token != MOCK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": settings.EVAL_USERNAME, "role": "admin"}

def get_authority_user(user: dict = Depends(get_current_user)):
    if user.get("role") not in {"admin", "authority", "operator"}:
        raise HTTPException(status_code=403, detail="Authority access required")
    return user

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if req.username == settings.EVAL_USERNAME and req.password == settings.EVAL_PASSWORD:
        return LoginResponse(token=MOCK_TOKEN, message="Login successful")
    raise HTTPException(status_code=401, detail="Invalid username or password")

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}

@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
