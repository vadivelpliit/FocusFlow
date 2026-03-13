from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    detail: str = Field(..., max_length=500)
    due_date: Optional[date] = None
    frequency: str = "once"
    comments: Optional[str] = None
    importance: Optional[str] = None  # P1, P2, P3
    time_horizon: Optional[str] = None  # focus_today, focus_week, focus_month, focus_later
    complexity: Optional[str] = None  # small, medium, large
    reasoning: Optional[str] = None  # AI explanation from last Prioritize run
    tags: Optional[List[str]] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    detail: Optional[str] = Field(None, max_length=500)
    due_date: Optional[date] = None
    frequency: Optional[str] = None
    comments: Optional[str] = None
    importance: Optional[str] = None
    time_horizon: Optional[str] = None
    complexity: Optional[str] = None
    reasoning: Optional[str] = None
    tags: Optional[List[str]] = None
    completed: Optional[bool] = None


class TaskResponse(TaskBase):
    id: int
    completed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schedule (Phase 4)
class UserScheduleInputResponse(BaseModel):
    day_of_week: int
    user_description: Optional[str] = None

    class Config:
        from_attributes = True


class UserScheduleInputBatch(BaseModel):
    inputs: List[UserScheduleInputResponse]


class ScheduleBlockBase(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    label: str
    notes: Optional[str] = None


class ScheduleBlockResponse(ScheduleBlockBase):
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True


class ScheduleBlockCreate(ScheduleBlockBase):
    pass


class ScheduleProposeRequest(BaseModel):
    desired_activities: Optional[List[str]] = None  # e.g. ["office", "exercise", "cook"]


class ScheduleBlockProposed(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    label: str
    notes: Optional[str] = None
