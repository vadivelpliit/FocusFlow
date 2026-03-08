import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..crud import (
    get_schedule_inputs,
    get_schedule_blocks,
    replace_schedule_blocks,
    set_schedule_input,
    get_day_log,
    set_day_log,
    get_day_logs_in_range,
    get_tasks_due_in_range,
)
from ..database import get_db
from ..llm.schedule import propose_schedule
from ..models import User
from ..llm.recommend import recommend_plan, get_recommend_window
from ..schemas import ScheduleBlockResponse, UserScheduleInputResponse

router = APIRouter(prefix="/schedule", tags=["schedule"])


class ScheduleInputItem(BaseModel):
    day_of_week: int
    user_description: Optional[str] = None


class ScheduleInputsPut(BaseModel):
    inputs: List[ScheduleInputItem]


class ScheduleProposeRequest(BaseModel):
    desired_activities: List[str] = []


class ScheduleBlockItem(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    label: str
    notes: Optional[str] = None


class ScheduleApplyRequest(BaseModel):
    blocks: List[ScheduleBlockItem]


def _inputs_to_response() -> List[dict]:
    # Build default 0-6, then overlay from DB in a route
    return []


@router.get("/inputs", response_model=List[UserScheduleInputResponse])
def list_schedule_inputs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get current week description: one row per day (0=Monday .. 6=Sunday)."""
    rows = get_schedule_inputs(db, current_user.id)
    by_day = {r.day_of_week: r for r in rows}
    return [
        UserScheduleInputResponse(
            day_of_week=d,
            user_description=by_day[d].user_description if d in by_day else None,
        )
        for d in range(7)
    ]


@router.put("/inputs")
def put_schedule_inputs(body: ScheduleInputsPut, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Set description for each day. Send inputs with day_of_week 0-6."""
    for item in body.inputs:
        if 0 <= item.day_of_week <= 6:
            set_schedule_input(db, current_user.id, item.day_of_week, item.user_description or None)
    return {"ok": True}


@router.get("/blocks", response_model=List[ScheduleBlockResponse])
def list_schedule_blocks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all schedule blocks (saved week plan)."""
    return get_schedule_blocks(db, current_user.id)


@router.post("/propose")
def propose_week_schedule(body: ScheduleProposeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate a proposed 7-day schedule from current descriptions + desired activities. Does not save."""
    try:
        rows = get_schedule_inputs(db, current_user.id)
        by_day = {r.day_of_week: r for r in rows}
        day_descriptions = [by_day.get(d) and by_day[d].user_description or "" for d in range(7)]
        blocks = propose_schedule(day_descriptions, body.desired_activities or [])
        return {"blocks": blocks}
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail="AI schedule is not configured. Set OPENAI_API_KEY.")
        raise


@router.post("/apply", response_model=List[ScheduleBlockResponse])
def apply_schedule(body: ScheduleApplyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Replace all schedule blocks with the given list (e.g. from propose)."""
    blocks = [b.model_dump() for b in body.blocks]
    return replace_schedule_blocks(db, current_user.id, blocks)


# --- Day log (what I did per calendar date) + AI recommend ---

class DayLogResponse(BaseModel):
    date: str
    content: Optional[str] = None


class DayLogPut(BaseModel):
    content: Optional[str] = None


@router.get("/day-log", response_model=DayLogResponse)
def get_day_log_route(
    date_str: str = Query(..., description="Date YYYY-MM-DD", alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get 'what I did' for a specific calendar date."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date, use YYYY-MM-DD")
    row = get_day_log(db, current_user.id, d)
    content = row.content if row else None
    logger.info("day-log GET date=%s found=%s content_len=%s", date_str, row is not None, len(content) if content else 0)
    if not row:
        return DayLogResponse(date=date_str, content=None)
    return DayLogResponse(date=date_str, content=row.content)


@router.put("/day-log", response_model=DayLogResponse)
def put_day_log_route(
    date_str: str = Query(..., description="Date YYYY-MM-DD", alias="date"),
    body: DayLogPut = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set 'what I did' for a specific calendar date (persisted)."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date, use YYYY-MM-DD")
    content_len = len(body.content) if body.content else 0
    logger.info("day-log PUT date=%s content_len=%s", date_str, content_len)
    set_day_log(db, current_user.id, d, body.content)
    logger.info("day-log PUT date=%s committed", date_str)
    return DayLogResponse(date=date_str, content=body.content)


class RecommendRequest(BaseModel):
    date: str  # YYYY-MM-DD anchor date


class RecommendResponse(BaseModel):
    recommendation: str
    window_start: str
    window_end: str


@router.post("/recommend", response_model=RecommendResponse)
def recommend_route(body: RecommendRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get AI recommendation for rest of this week + next week, learning from past 'what I did' logs."""
    try:
        anchor = date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date, use YYYY-MM-DD")
    try:
        start, end = get_recommend_window(anchor)
        past_start = anchor - timedelta(days=30)
        past_logs = get_day_logs_in_range(db, current_user.id, past_start, anchor - timedelta(days=1))
        past_data = [{"date": str(r.date), "content": r.content} for r in past_logs]
        blocks = get_schedule_blocks(db, current_user.id)
        tasks_due = get_tasks_due_in_range(db, current_user.id, start, end)
        recommendation = recommend_plan(anchor, past_data, blocks, tasks_due)
        return RecommendResponse(
            recommendation=recommendation,
            window_start=start.isoformat(),
            window_end=end.isoformat(),
        )
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail="AI recommend is not configured. Set OPENAI_API_KEY.")
        raise
