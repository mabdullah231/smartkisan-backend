"""
Daily farming suggestion generation via Gemini (JSON output).
Uses saved farm coordinates, Weather API, IoT soil status, and prior stored suggestions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx

try:
    from google import genai
except Exception:  # pragma: no cover
    genai = None

from models.api import APIConfig
from models.auth import Iot_Configuration, User
from models.suggestion import UserSuggestion

logger = logging.getLogger(__name__)

TZ = ZoneInfo(os.getenv("SUGGESTION_TIMEZONE", "Asia/Karachi"))

SUGGESTION_JSON_PROMPT = """
You are Smart Kisan — an expert assistant for wheat (gandum) farmers in Pakistan.

**Task:** Produce ONE daily pack for the farmer for the given calendar day. Output must be
valid JSON only (no markdown fences, no commentary).

**Fields (exact keys):**
- "eng_title": Short recommendation line in English (max ~80 characters). This is the "action headline"
  (e.g. irrigation hint, spray timing, field check). It will show as a small dashboard card and as the calendar event title.
- "ur_title": Same meaning in Urdu script (max ~80 characters).
- "eng_description": 2–4 sentences in simple English: practical daily advice for wheat, grounded in the
  weather and soil data provided. Mention concrete next steps (when to irrigate, what to watch, safety).
- "ur_description": Same content in Urdu script, same length class.

**Rules:**
- Wheat only; if context is unclear, still give safe, generic wheat-care advice for Punjab/Sindh conditions.
- Be consistent with prior days' advice: do not contradict yesterday's irrigation plan without explaining why weather/soil changed.
- Use village-friendly units (acre, bag) where helpful.
- Never invent numeric sensor values; only use numbers given in context.
- If soil data is missing, say irrigation should follow weather and field observation without claiming a sensor reading.

**Context JSON (input):**
{context_json}
"""


def advice_date_today() -> date:
    return datetime.now(TZ).date()


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_suggestion_json(raw: str) -> Dict[str, str]:
    cleaned = _strip_json_fence(raw)
    data = json.loads(cleaned)
    for key in ("eng_title", "ur_title", "eng_description", "ur_description"):
        if key not in data or not isinstance(data[key], str):
            raise ValueError(f"Missing or invalid field: {key}")
        data[key] = data[key].strip()
    if len(data["eng_title"]) > 512:
        data["eng_title"] = data["eng_title"][:512]
    if len(data["ur_title"]) > 512:
        data["ur_title"] = data["ur_title"][:512]
    return data


async def _weather_snapshot(lat: float, lon: float) -> Dict[str, Any]:
    config = await APIConfig.filter(category="Weather", is_active=True).first()
    if not config:
        raise RuntimeError("Weather APIConfig not found")

    async with httpx.AsyncClient(timeout=30.0) as client:
        params_en = {
            "q": f"{lat},{lon}",
            "key": config.api_key,
            "lang": "en",
        }
        params_ur = {
            "q": f"{lat},{lon}",
            "key": config.api_key,
            "lang": "ur",
        }
        if config.extra_config and isinstance(config.extra_config, dict):
            params_en.update(config.extra_config)
            params_ur.update(config.extra_config)

        response_en, response_ur = await asyncio.gather(
            client.get(config.base_url, params=params_en),
            client.get(config.base_url, params=params_ur),
            return_exceptions=True,
        )

        if isinstance(response_en, Exception) or response_en.status_code != 200:
            raise RuntimeError("Weather API request failed")

        data_en = response_en.json()
        current_en = data_en.get("current", {})
        condition_en = current_en.get("condition", {})
        condition_text_urdu = None
        if isinstance(response_ur, httpx.Response) and response_ur.status_code == 200:
            data_ur = response_ur.json()
            current_ur = data_ur.get("current", {})
            condition_ur = current_ur.get("condition", {})
            condition_text_urdu = condition_ur.get("text")

        return {
            "temp_c": current_en.get("temp_c"),
            "humidity_pct": current_en.get("humidity"),
            "condition_en": condition_en.get("text"),
            "condition_ur": condition_text_urdu,
            "location_label": data_en.get("location", {}).get("name"),
        }


async def _iot_snapshot(user: User) -> Optional[Dict[str, Any]]:
    iot_config = await Iot_Configuration.filter(user=user).order_by("-created_at").first()
    if not iot_config or not iot_config.device_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(iot_config.device_url)
            response.raise_for_status()
            data = response.json()
            # Check for actual device fields: "value" and "soil_status"
            if "value" not in data or "soil_status" not in data:
                return None
            # Return in normalized format for Gemini
            return {
                "raw": data.get("value"),
                "status": data.get("soil_status"),
                "timestamp": data.get("lastTimestamp"),
                "device_status": data.get("status")  # online/offline
            }
    except Exception as e:
        logger.warning("IoT fetch failed for user %s: %s", user.id, e)
        return None


async def _prior_suggestions_context(user_id: int, before_date: date, limit: int = 3) -> List[Dict[str, Any]]:
    rows = (
        await UserSuggestion.filter(user_id=user_id, advice_date__lt=before_date)
        .order_by("-advice_date")
        .limit(limit)
    )
    out: List[Dict[str, Any]] = []
    for r in reversed(rows):
        out.append(
            {
                "advice_date": r.advice_date.isoformat(),
                "eng_title": r.eng_title,
                "ur_title": r.ur_title,
                "eng_description": r.eng_description[:500],
                "ur_description": r.ur_description[:500],
            }
        )
    return out


async def generate_suggestion_payload(
    user: User,
    target_date: Optional[date] = None,
) -> Dict[str, str]:
    """Call Gemini and return parsed title/description fields."""
    if genai is None:
        raise RuntimeError("google-genai not installed")

    api = await APIConfig.filter(is_active=True, provider__iexact="GEMINI").first()
    if not api or not api.api_key:
        raise RuntimeError("Gemini API not configured")

    if user.farm_latitude is None or user.farm_longitude is None:
        raise ValueError("User has no saved farm coordinates")

    lat = float(user.farm_latitude)
    lon = float(user.farm_longitude)

    weather_task = asyncio.create_task(_weather_snapshot(lat, lon))
    iot_task = asyncio.create_task(_iot_snapshot(user))
    d = target_date if target_date is not None else advice_date_today()
    prior_task = asyncio.create_task(_prior_suggestions_context(user.id, d, limit=3))

    weather, iot, prior = await asyncio.gather(weather_task, iot_task, prior_task, return_exceptions=True)

    # Handle failures gracefully
    if isinstance(weather, Exception):
        logger.warning("Weather fetch failed: %s", weather)
        weather = None
    if isinstance(iot, Exception):
        logger.warning("IoT fetch failed: %s", iot)
        iot = None
    if isinstance(prior, Exception):
        logger.warning("Prior suggestions fetch failed: %s", prior)
        prior = []

    context = {
        "advice_date": d.isoformat(),
        "timezone": str(TZ),
        "farmer_name": user.name,
        "farm_coordinates": {"latitude": lat, "longitude": lon},
        "weather": weather,
        "soil_sensor": iot,
        "previous_days_advice": prior,
    }

    context_json = json.dumps(context, ensure_ascii=False)
    prompt = SUGGESTION_JSON_PROMPT.format(context_json=context_json)

    os.environ["GEMINI_API_KEY"] = api.api_key
    client = genai.Client()

    model_name = "gemini-2.5-flash"
    try:
        if api.extra_config and isinstance(api.extra_config, dict) and api.extra_config.get("model"):
            model_name = api.extra_config.get("model")
    except Exception:
        pass

    response = await client.aio.models.generate_content(
        model=model_name, contents=prompt
    )
    raw_text = getattr(response, "text", None) or ""
    if not raw_text.strip():
        raise RuntimeError("Empty Gemini response")

    return parse_suggestion_json(raw_text)


async def upsert_suggestion_for_date(
    user: User,
    advice_date: date,
    payload: Dict[str, str],
) -> UserSuggestion:
    row, created = await UserSuggestion.get_or_create(
        user=user,
        advice_date=advice_date,
        defaults={
            "eng_title": payload["eng_title"],
            "ur_title": payload["ur_title"],
            "eng_description": payload["eng_description"],
            "ur_description": payload["ur_description"],
        },
    )
    if not created:
        row.eng_title = payload["eng_title"]
        row.ur_title = payload["ur_title"]
        row.eng_description = payload["eng_description"]
        row.ur_description = payload["ur_description"]
        await row.save()
    return row


async def generate_and_store_for_user(user_id: int) -> Optional[UserSuggestion]:
    """Generate today's suggestion for one user. Skips if no farm coords or inactive."""
    user = await User.filter(id=user_id).first()
    if not user or not user.is_active:
        return None
    if user.farm_latitude is None or user.farm_longitude is None:
        logger.info("Skipping suggestion generation: user %s has no farm coordinates", user_id)
        return None

    d = advice_date_today()
    try:
        payload = await generate_suggestion_payload(user, target_date=d)
        return await upsert_suggestion_for_date(user, d, payload)
    except Exception as e:
        logger.exception("Suggestion generation failed for user %s: %s", user_id, e)
        return None


async def run_suggestion_job_for_all_users() -> Tuple[int, int]:
    """
    Process all active users with farm coordinates. Returns (success_count, fail_count).
    """
    users = await User.filter(
        is_active=True,
        farm_latitude__not_isnull=True,
        farm_longitude__not_isnull=True,
    ).all()
    user_ids = [u.id for u in users]

    ok = 0
    fail = 0
    for uid in user_ids:
        row = await generate_and_store_for_user(uid)
        if row:
            ok += 1
        else:
            fail += 1
    logger.info("Suggestion job finished: ok=%s fail=%s", ok, fail)
    return ok, fail
