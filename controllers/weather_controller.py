from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
import httpx
from models.api import APIConfig 
from helpers.token_helper import get_current_user
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from models.auth import User
from tortoise.exceptions import DoesNotExist
import asyncio

weather_router = APIRouter(prefix="/weather")


class WeatherRequest(BaseModel):
    latitude: float
    longitude: float

class WeatherResponse(BaseModel):
    success: bool
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    condition_text: Optional[str] = None
    condition_text_urdu: Optional[str] = None 
    condition_icon: Optional[str] = None
    error: Optional[str] = None



@weather_router.post("/get-weather", response_model=WeatherResponse)
async def get_weather_data(
    weather_request: WeatherRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        config = await APIConfig.get(category="Weather", is_active=True)
        
        # Make two parallel API calls for English and Urdu
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare English parameters
            params_en = {
                "q": f"{weather_request.latitude},{weather_request.longitude}",
                "key": config.api_key,
                "lang": "en"  # English
            }
            
            # Prepare Urdu parameters
            params_ur = {
                "q": f"{weather_request.latitude},{weather_request.longitude}",
                "key": config.api_key,
                "lang": "ur"  # Urdu
            }
            
            # Add any extra parameters from config to both
            if config.extra_config:
                params_en.update(config.extra_config)
                params_ur.update(config.extra_config)
            
            # Make both requests concurrently
            response_en, response_ur = await asyncio.gather(
                client.get(config.base_url, params=params_en),
                client.get(config.base_url, params=params_ur),
                return_exceptions=True
            )
            
            # Check if English request was successful
            if isinstance(response_en, Exception) or response_en.status_code != 200:
                raise HTTPException(
                    status_code=response_en.status_code if hasattr(response_en, 'status_code') else 500,
                    detail=f"Weather API error"
                )
            
            data_en = response_en.json()
            current_en = data_en.get("current", {})
            condition_en = current_en.get("condition", {})
            
            # Get Urdu text if Urdu request was successful
            condition_text_urdu = None
            if isinstance(response_ur, httpx.Response) and response_ur.status_code == 200:
                data_ur = response_ur.json()
                current_ur = data_ur.get("current", {})
                condition_ur = current_ur.get("condition", {})
                condition_text_urdu = condition_ur.get("text")
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "temperature": current_en.get("temp_c"),
                    "humidity": current_en.get("humidity"),
                    "condition_text": condition_en.get("text"),
                    "condition_text_urdu": condition_text_urdu,  # Added Urdu text
                    "condition_icon": condition_en.get("icon")
                }
            )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Weather API request timeout"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Weather API connection error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching weather data: {str(e)}"
        )