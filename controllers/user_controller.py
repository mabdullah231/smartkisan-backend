from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from models.auth import User
from helpers.token_helper import get_current_user
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tortoise.exceptions import DoesNotExist

# Router setup
user_router = APIRouter(prefix="/admin/userdata")

# Constants for user types
ADMIN_USER_TYPE = 0
SUBADMIN_USER_TYPE = 1
REGULAR_USER_TYPE = 2

# Response models
class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    user_type: int
    is_active: bool

class UserListResponse(BaseModel):
    success: bool
    data: List[UserResponse]

class StatusToggleResponse(BaseModel):
    success: bool
    detail: str
    is_active: bool

class RoleChangeResponse(BaseModel):
    success: bool
    detail: str
    user_type: int

# Endpoints
@user_router.get("/get-all", response_model=UserListResponse)
async def get_all_users(
    current_user: User = Depends(get_current_user)
):
    """
    Get all users (admin only)
    """
    try:
        # Verify admin access
        if current_user.user_type not in {ADMIN_USER_TYPE, SUBADMIN_USER_TYPE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can access this endpoint"
            )

        # Get all users
        # users = await User.all()
        users = await User.exclude(id=current_user.id).all()


        # Convert to response format
        user_list = [
            UserResponse(
                id=user.id,
                name=user.name,
                phone=user.phone,
                user_type=user.user_type,
                is_active=user.is_active
            )
            for user in users
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": [user.model_dump() for user in user_list]
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@user_router.put("/toggle-status/{user_id}", response_model=StatusToggleResponse)
async def toggle_user_status(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Toggle user active status (admin only)
    """
    try:
        # Verify admin access
        if current_user.user_type not in {ADMIN_USER_TYPE, SUBADMIN_USER_TYPE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can access this endpoint"
            )

        # Prevent modifying self
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own status"
            )

        # Get the user
        try:
            user = await User.get(id=user_id)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Toggle status
        user.is_active = not user.is_active
        await user.save()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "detail": "User status updated successfully",
                "is_active": user.is_active
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling user status: {str(e)}"
        )

@user_router.put("/make-subadmin/{user_id}", response_model=RoleChangeResponse)
async def make_user_subadmin(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Make user a subadmin (admin only)
    """
    try:
        # Verify admin access
        if current_user.user_type not in {ADMIN_USER_TYPE, SUBADMIN_USER_TYPE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can access this endpoint"
            )

        # Prevent modifying self
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own role"
            )

        # Get the user
        try:
            user = await User.get(id=user_id)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Only regular users can be made subadmins
        if user.user_type != REGULAR_USER_TYPE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only regular users can be made subadmins"
            )

        # Update role
        user.user_type = SUBADMIN_USER_TYPE
        await user.save()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "detail": "User role updated to subadmin",
                "user_type": user.user_type
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )