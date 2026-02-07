from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from models.auth import User
from models.api import APIConfig
from helpers.token_helper import get_current_user
from typing import Annotated, Optional
from fastapi.responses import StreamingResponse
import random 
import string
import os 


# Pydantic models for admin users
class UserTogglePayload(BaseModel):
    is_active: bool


# Pydantic models for validation
class APIConfigPayload(BaseModel):
    category: str
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    extra_config: Optional[dict] = None
    is_active: bool = True


admin_router = APIRouter()


# GET all API configurations
@admin_router.get("/apis")
async def get_all_apis(user: Annotated[User, Depends(get_current_user)]):
    # Only admins can access
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access API configurations")
    
    try:
        apis = await APIConfig.all().values(
            "id", "category", "provider", "api_key", "base_url", 
            "extra_config", "is_active", "created_at", "updated_at"
        )
        return {"success": True, "apis": apis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching APIs: {str(e)}")


# GET single API configuration
@admin_router.get("/apis/{api_id}")
async def get_api(api_id: int, user: Annotated[User, Depends(get_current_user)]):
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access API configurations")
    
    try:
        api = await APIConfig.get_or_none(id=api_id)
        if not api:
            raise HTTPException(status_code=404, detail="API configuration not found")
        
        return {
            "success": True,
            "api": {
                "id": api.id,
                "category": api.category,
                "provider": api.provider,
                "api_key": api.api_key,
                "base_url": api.base_url,
                "extra_config": api.extra_config,
                "is_active": api.is_active,
                "created_at": api.created_at,
                "updated_at": api.updated_at,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching API: {str(e)}")


# POST create new API configuration
@admin_router.post("/apis")
async def create_api(
    data: APIConfigPayload,
    user: Annotated[User, Depends(get_current_user)]
):
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create API configurations")
    
    try:
        api = await APIConfig.create(
            category=data.category,
            provider=data.provider,
            api_key=data.api_key,
            base_url=data.base_url,
            extra_config=data.extra_config,
            is_active=data.is_active
        )
        
        return {
            "success": True,
            "detail": "API configuration created successfully",
            "api": {
                "id": api.id,
                "category": api.category,
                "provider": api.provider,
                "api_key": api.api_key,
                "base_url": api.base_url,
                "extra_config": api.extra_config,
                "is_active": api.is_active,
                "created_at": api.created_at,
                "updated_at": api.updated_at,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating API: {str(e)}")


# PUT edit API configuration
@admin_router.put("/apis/{api_id}")
async def update_api(
    api_id: int,
    data: APIConfigPayload,
    user: Annotated[User, Depends(get_current_user)]
):
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit API configurations")
    
    try:
        api = await APIConfig.get_or_none(id=api_id)
        if not api:
            raise HTTPException(status_code=404, detail="API configuration not found")
        
        api.category = data.category
        api.provider = data.provider
        api.api_key = data.api_key
        api.base_url = data.base_url
        api.extra_config = data.extra_config
        api.is_active = data.is_active
        await api.save()
        
        return {
            "success": True,
            "detail": "API configuration updated successfully",
            "api": {
                "id": api.id,
                "category": api.category,
                "provider": api.provider,
                "api_key": api.api_key,
                "base_url": api.base_url,
                "extra_config": api.extra_config,
                "is_active": api.is_active,
                "created_at": api.created_at,
                "updated_at": api.updated_at,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating API: {str(e)}")


# DELETE API configuration
@admin_router.delete("/apis/{api_id}")
async def delete_api(
    api_id: int,
    user: Annotated[User, Depends(get_current_user)]
):
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete API configurations")
    
    try:
        api = await APIConfig.get_or_none(id=api_id)
        if not api:
            raise HTTPException(status_code=404, detail="API configuration not found")
        
        await api.delete()
        
        return {
            "success": True,
            "detail": "API configuration deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting API: {str(e)}")


# GET all non-admin users (for admin users management page)
@admin_router.get("/users")
async def get_all_non_admin_users(user: Annotated[User, Depends(get_current_user)]):
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access user list")
    try:
        users = await User.exclude(user_role="admin").values(
            "id", "name", "phone", "is_active", "user_role"
        )
        # Map to frontend shape: id, name, phone, email, is_active, joined_at (User has no email/created_at)
        out = []
        for u in users:
            out.append({
                "id": u["id"],
                "name": u["name"],
                "phone": u["phone"],
                "email": None,
                "is_active": u["is_active"],
                "joined_at": None,
            })
        return {"success": True, "users": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


# PATCH enable/disable a non-admin user
@admin_router.patch("/users/{user_id}")
async def set_user_active(
    user_id: int,
    data: UserTogglePayload,
    user: Annotated[User, Depends(get_current_user)],
):
    if user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update user status")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")
    try:
        target = await User.get_or_none(id=user_id)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if target.user_role == "admin":
            raise HTTPException(status_code=400, detail="Cannot change status of an admin")
        target.is_active = data.is_active
        await target.save()
        return {"success": True, "detail": "User status updated", "is_active": target.is_active}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")
