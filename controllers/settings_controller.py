from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Annotated, Optional
from models.auth import User as User, Iot_Configuration
from models.auth import Iot_Configuration as Iot_Configuration
from helpers.token_helper import get_current_user
from helpers.phone_validator import validate_pakistani_phone
from argon2 import PasswordHasher
from fastapi.responses import JSONResponse

# Password hashing context
ph = PasswordHasher()

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
    type: str  # "profile", "password", or "iot"
    full_name: Optional[str] = None
    phone: Optional[str] = None
    current_password: Optional[str] = None
    confirm_password: Optional[str] = None
    new_password: Optional[str] = None
    iot_url: Optional[str] = None
    
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        return validate_pakistani_phone(str(v))

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except:
        return False

def get_password_hash(password: str) -> str:
    return ph.hash(password)

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
            print(f"Password update request: current={request.current_password[:3]}..., new={request.new_password[:3]}..., confirm={request.confirm_password[:3]}...")
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
            print(f"Verifying current password for user {user.id}, hash starts with {user.password[:10]}...")
            is_valid = verify_password(request.current_password, user.password)
            print(f"Password valid: {is_valid}")
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password
            print("Hashing new password")
            new_hash = get_password_hash(request.new_password)
            print(f"New hash starts with {new_hash[:10]}...")
            user.password = new_hash
            print("Saving user")
            await user.save()
            print("User saved successfully")
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "detail": "Password updated successfully"}
            )
        
        elif request.type == "iot":
            if request.iot_url is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="IoT URL is required"
                )
            Iot_Configuration_obj = await Iot_Configuration.filter(user_id=user.id).first()
            if Iot_Configuration_obj:
                Iot_Configuration_obj.device_url = request.iot_url
                await Iot_Configuration_obj.save()
            else:
                Iot_Configuration_obj = await Iot_Configuration.create(
                    device_url=request.iot_url,
                    user_id=user.id
                )
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "detail": "IoT device URL saved successfully"}
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid settings type"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {e}"
        )


# optional helper route for retrieving only IoT configuration
@settings_router.get("/user/iot")
async def get_user_iot(
    current_user: Annotated[User, Depends(get_current_user)]
):
    try:
        iot_config = await Iot_Configuration.filter(user_id=current_user.id).order_by("-created_at").first()
        return {"success": True, "iot_url": iot_config.device_url if iot_config and iot_config.device_url else ""}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching IoT configuration: {str(e)}"
        )

@settings_router.get("/user/profile")
async def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)]
):
    try:
        user = await User.filter(id=current_user.id).first()
        # also fetch latest IoT configuration for this user
        iot_config = await Iot_Configuration.filter(user_id=user.id).order_by("-created_at").first()
        iot_url = iot_config.device_url if iot_config and iot_config.device_url else ""
        return {
            "success": True,
            "data": {
                "full_name": user.name,
                "phone": user.phone,
                "iot_url": iot_url,
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )
