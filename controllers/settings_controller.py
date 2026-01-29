from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Annotated, Optional
from models.auth import User as User

from helpers.token_helper import get_current_user
from helpers.phone_validator import validate_pakistani_phone
from passlib.context import CryptContext
from fastapi.responses import JSONResponse

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Router setup
settings_router = APIRouter(prefix="/settings")

# Constants for user types
ADMIN_USER_TYPE = 0
SUBADMIN_USER_TYPE = 1
REGULAR_USER_TYPE = 2

# Request models
class ProfileUpdatePayload(BaseModel):
    full_name: str
    phone: str
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            raise ValueError("Phone number is required")
        return validate_pakistani_phone(str(v))

class PasswordUpdatePayload(BaseModel):
    current_password: str
    new_password: str

class AdminAiConfigPayload(BaseModel):
    api_key: str
    model_name: str
    # temperature: float = 0.5

class SettingsRequest(BaseModel):
    type: str  # "profile" or "password"
    full_name: Optional[str] = None
    phone: Optional[str] = None
    current_password: Optional[str] = None
    confirm_password: Optional[str] = None
    new_password: Optional[str] = None
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        return validate_pakistani_phone(str(v))

# Helper functions
async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# User Settings Endpoints
@settings_router.post("/user/settings")
async def update_user_settings(
    request: SettingsRequest,
    current_user: Annotated[User , Depends(get_current_user)]
):
    try:
        user = await User.filter(id=current_user.id).first()
        
        if request.type == "profile":
            # Check if at least one of the fields is provided
            if not request.full_name and not request.phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one of full name or phone is required"
                )
            
            # Update profile fields if provided
            if request.full_name:
                user.name = request.full_name
            if request.phone:
                user.phone = request.phone
            
            await user.save()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "detail": "Profile updated successfully"}
            )
        
        elif request.type == "password":
            if not request.current_password or not request.new_password or not request.confirm_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All password fields are required"
                )
            
            if request.new_password != request.confirm_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password and confirmation do not match"
                )
            
            # Verify current password
            if not await verify_password(request.current_password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password
            user.password = await get_password_hash(request.new_password)
            await user.save()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "detail": "Password updated successfully"}
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid settings type"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {str(e)}"
        )

@settings_router.get("/user/profile")
async def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    try:
        user = await User.filter(id=current_user.id).first()
        return {
            "success": True,
            "data": {
                "full_name": user.name,
                "phone": user.phone
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )
