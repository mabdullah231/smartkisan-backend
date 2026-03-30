import os
from datetime import date, datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from tortoise.exceptions import IntegrityError

from helpers.suggestion_generator import (
    advice_date_today,
    generate_and_store_for_user,
    run_suggestion_job_for_all_users,
)
from helpers.token_helper import get_current_user
from models.auth import User
from models.suggestion import UserSuggestion

suggestion_router = APIRouter(prefix="/suggestions")


class SuggestionPayload(BaseModel):
    """Body for create/update (e.g. future cron or admin tooling)."""

    advice_date: date
    eng_title: str = Field(..., max_length=512)
    ur_title: str = Field(..., max_length=512)
    eng_description: str
    ur_description: str


class SuggestionItem(BaseModel):
    id: int
    advice_date: date
    eng_title: str
    ur_title: str
    eng_description: str
    ur_description: str
    created_at: datetime
    updated_at: datetime


def _row_to_item(row: UserSuggestion) -> SuggestionItem:
    return SuggestionItem(
        id=row.id,
        advice_date=row.advice_date,
        eng_title=row.eng_title,
        ur_title=row.ur_title,
        eng_description=row.eng_description,
        ur_description=row.ur_description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@suggestion_router.get("/me")
async def get_my_suggestion_for_date(
    current_user: Annotated[User, Depends(get_current_user)],
    advice_date: Optional[date] = Query(
        None,
        description="Calendar day (YYYY-MM-DD). Defaults to today in SUGGESTION_TIMEZONE (Asia/Karachi).",
    ),
):
    """
    Dashboard recommendation (title) + daily advice (description) for one day.
    """
    d = advice_date if advice_date is not None else advice_date_today()
    row = await UserSuggestion.filter(user_id=current_user.id, advice_date=d).first()
    if not row:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "data": None, "advice_date": d.isoformat()},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": _row_to_item(row).model_dump(mode="json"),
            "advice_date": d.isoformat(),
        },
    )


@suggestion_router.get("/me/history")
async def get_my_suggestion_history(
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(
        7,
        ge=1,
        le=90,
        description="Number of past days to include (ending yesterday or including today — see behaviour).",
    ),
    include_today: bool = Query(
        True,
        description="If true, the range ends on today; otherwise ends on yesterday.",
    ),
):
    """
    Recent suggestions for context (e.g. last 3 days before calling Gemini).
    Rows ordered by advice_date descending (newest first).
    """
    today = advice_date_today()
    end = today if include_today else today - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    rows = (
        await UserSuggestion.filter(
            user_id=current_user.id,
            advice_date__gte=start,
            advice_date__lte=end,
        )
        .order_by("-advice_date")
        .all()
    )
    items: List[dict] = [_row_to_item(r).model_dump(mode="json") for r in rows]
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": items,
            "range": {"start": start.isoformat(), "end": end.isoformat()},
        },
    )


@suggestion_router.put("/me")
async def upsert_my_suggestion(
    payload: SuggestionPayload,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create or replace the suggestion for the given advice_date (same user).
    Intended for internal/cron use later; callable now for testing with a normal user JWT.
    """
    try:
        row, created = await UserSuggestion.get_or_create(
            user=current_user,
            advice_date=payload.advice_date,
            defaults={
                "eng_title": payload.eng_title,
                "ur_title": payload.ur_title,
                "eng_description": payload.eng_description,
                "ur_description": payload.ur_description,
            },
        )
        if not created:
            row.eng_title = payload.eng_title
            row.ur_title = payload.ur_title
            row.eng_description = payload.eng_description
            row.ur_description = payload.ur_description
            await row.save()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "created": created,
                "data": _row_to_item(row).model_dump(mode="json"),
            },
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not upsert suggestion: {e}",
        )


@suggestion_router.delete("/me/{advice_date}")
async def delete_my_suggestion_for_date(
    advice_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Remove a stored suggestion for a calendar day (optional cleanup / testing)."""
    deleted = await UserSuggestion.filter(
        user_id=current_user.id, advice_date=advice_date
    ).delete()
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No suggestion for that date",
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "detail": "Deleted"},
    )


@suggestion_router.get("/me/calendar")
async def get_my_suggestions_for_calendar_range(
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: date = Query(..., description="Inclusive start (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Inclusive end (YYYY-MM-DD)"),
):
    """All stored suggestions in a date range (for FullCalendar)."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    rows = (
        await UserSuggestion.filter(
            user_id=current_user.id,
            advice_date__gte=start_date,
            advice_date__lte=end_date,
        )
        .order_by("advice_date")
        .all()
    )
    items: List[dict] = [_row_to_item(r).model_dump(mode="json") for r in rows]
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "data": items},
    )


@suggestion_router.post("/me/refresh")
async def refresh_my_suggestion_now(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Regenerate today's suggestion for the logged-in user (Gemini + weather + IoT).
    Requires farm coordinates in Settings.
    """
    if current_user.farm_latitude is None or current_user.farm_longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Farm location not set. Add it under Settings → IoT Device.",
        )
    row = await generate_and_store_for_user(current_user.id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate suggestion. Check Gemini/weather configuration and server logs.",
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "data": _row_to_item(row).model_dump(mode="json"),
        },
    )


@suggestion_router.post("/internal/run")
async def internal_run_suggestion_job(
    x_cron_secret: Annotated[Optional[str], Header(alias="X-Cron-Secret")] = None,
):
    """
    Run the same job as the scheduler (all users with farm coords). Protect with CRON_SECRET env.
    """
    expected = os.getenv("CRON_SECRET")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET is not configured on the server",
        )
    if not x_cron_secret or x_cron_secret != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    ok, fail = await run_suggestion_job_for_all_users()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "generated_ok": ok, "failed": fail},
    )
