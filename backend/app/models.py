from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, JSON, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)  # one-time, short-lived
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    detail = Column(String(500), nullable=False)
    due_date = Column(Date, nullable=True)
    frequency = Column(String(20), default="once")  # once, daily, weekly, monthly
    comments = Column(Text, nullable=True)  # next steps / notes
    importance = Column(String(10), nullable=True)  # P1, P2, P3 (priority / consequence)
    time_horizon = Column(String(20), nullable=True)  # focus_today, focus_week, focus_month, focus_later
    complexity = Column(String(10), nullable=True)  # small, medium, large
    reasoning = Column(Text, nullable=True)  # AI explanation for focus/priority (from last Prioritize run)
    tags = Column(JSON, nullable=True)  # list of strings e.g. ["financial", "call"]
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # e.g. "09:00"
    end_time = Column(String(10), nullable=False)
    label = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class UserScheduleInput(Base):
    __tablename__ = "user_schedule_inputs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    user_description = Column(Text, nullable=True)


class DayLog(Base):
    """What I did on a specific calendar date (persisted memory per date)."""
    __tablename__ = "day_logs"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_day_log_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=True)
