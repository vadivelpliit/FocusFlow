from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Enum, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    detail = Column(String(500), nullable=False)
    due_date = Column(Date, nullable=True)
    frequency = Column(String(20), default="once")  # once, daily, weekly, monthly
    comments = Column(Text, nullable=True)  # next steps / notes
    importance = Column(String(10), nullable=True)  # P1, P2, P3
    time_horizon = Column(String(20), nullable=True)  # focus_now, focus_today, focus_week, focus_month, focus_later
    tags = Column(JSON, nullable=True)  # list of strings e.g. ["financial", "call"]
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # e.g. "09:00"
    end_time = Column(String(10), nullable=False)
    label = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class UserScheduleInput(Base):
    __tablename__ = "user_schedule_inputs"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False)
    user_description = Column(Text, nullable=True)


class DayLog(Base):
    """What I did on a specific calendar date (persisted memory per date)."""
    __tablename__ = "day_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    content = Column(Text, nullable=True)
