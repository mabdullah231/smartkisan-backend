from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import httpx
from models.auth import User
from models.auth import Iot_Configuration  # adjust import path as needed
from helpers.token_helper import get_current_user

iot_router = APIRouter(prefix="/iot", tags=["IoT"])

@iot_router.get("/status")
async def get_iot_status(user: Annotated[User, Depends(get_current_user)]):
    """
    Fetch the current status from the user's IoT device.
    The device URL is taken from the user's IoT configuration(s).
    Expected response from device: {"raw":4095,"status":"Super Dry"}
    """
    # Fetch the user's IoT configuration(s) - assuming one per user, or take the latest
    iot_config = await Iot_Configuration.filter(user=user).order_by("-created_at").first()
    if not iot_config or not iot_config.device_url:
        raise HTTPException(status_code=404, detail="IoT device URL not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(iot_config.device_url)
            response.raise_for_status()
            data = response.json()
            # Validate expected fields from IoT device
            if "value" not in data or "soil_status" not in data:
                raise HTTPException(status_code=502, detail="Invalid response format from IoT device")
            
            # Transform response to match frontend expectations
            transformed_data = {
                "raw": data.get("value"),           # Sensor reading
                "status": data.get("soil_status"),  # Soil status (e.g., "Very Dry", "Dry")
                "lastTimestamp": data.get("lastTimestamp"),  # Include timestamp for reference
                "deviceStatus": data.get("status")  # Device online/offline status
            }
            return {"success": True, "data": transformed_data}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="IoT device request timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"IoT device returned error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch IoT status: {str(e)}")