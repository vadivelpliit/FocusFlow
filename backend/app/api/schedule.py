from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..crud import (
    get_schedule_inputs,
    get_schedule_blocks,
    replace_schedule_blocks,
    set_schedule_input,
)
from ..database import get_db
from ..llm.schedule import propose_schedule
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
def list_schedule_inputs(db: Session = Depends(get_db)):
    """Get current week description: one row per day (0=Monday .. 6=Sunday)."""
    rows = get_schedule_inputs(db)
    by_day = {r.day_of_week: r for r in rows}
    return [
        UserScheduleInputResponse(
            day_of_week=d,
            user_description=by_day[d].user_description if d in by_day else None,
        )
        for d in range(7)
    ]


@router.put("/inputs")
def put_schedule_inputs(body: ScheduleInputsPut, db: Session = Depends(get_db)):
    """Set description for each day. Send inputs with day_of_week 0-6."""
    for item in body.inputs:
        if 0 <= item.day_of_week <= 6:
            set_schedule_input(db, item.day_of_week, item.user_description or None)
    return {"ok": True}


@router.get("/blocks", response_model=List[ScheduleBlockResponse])
def list_schedule_blocks(db: Session = Depends(get_db)):
    """Get all schedule blocks (saved week plan)."""
    return get_schedule_blocks(db)


@router.post("/propose")
def propose_week_schedule(body: ScheduleProposeRequest, db: Session = Depends(get_db)):
    """Generate a proposed 7-day schedule from current descriptions + desired activities. Does not save."""
    try:
        rows = get_schedule_inputs(db)
        by_day = {r.day_of_week: r for r in rows}
        day_descriptions = [by_day.get(d) and by_day[d].user_description or "" for d in range(7)]
        blocks = propose_schedule(day_descriptions, body.desired_activities or [])
        return {"blocks": blocks}
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail="AI schedule is not configured. Set OPENAI_API_KEY.")
        raise


@router.post("/apply", response_model=List[ScheduleBlockResponse])
def apply_schedule(body: ScheduleApplyRequest, db: Session = Depends(get_db)):
    """Replace all schedule blocks with the given list (e.g. from propose)."""
    blocks = [b.model_dump() for b in body.blocks]
    return replace_schedule_blocks(db, blocks)
