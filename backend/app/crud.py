from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Task, ScheduleBlock, UserScheduleInput, DayLog, User, PasswordResetToken
from .schemas import TaskCreate, TaskUpdate


# --- User & password reset ---
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username.strip()).first()


def create_user(db: Session, email: str, username: str, password_hash: str) -> User:
    u = User(email=email.lower().strip(), username=username.strip(), password_hash=password_hash)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def create_password_reset_token(db: Session, user_id: int, token: str, expires_at: datetime) -> PasswordResetToken:
    # Invalidate any existing tokens for this user
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
    row = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_password_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    return db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expires_at > datetime.utcnow(),
    ).first()


def delete_password_reset_token(db: Session, token: str) -> None:
    db.query(PasswordResetToken).filter(PasswordResetToken.token == token).delete()
    db.commit()


# --- Tasks (user-scoped) ---
def get_task(db: Session, task_id: int, user_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()


def get_tasks(
    db: Session,
    user_id: int,
    completed: Optional[bool] = None,
    importance: Optional[str] = None,
    time_horizon: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Task]:
    q = db.query(Task).filter(Task.user_id == user_id)
    if completed is not None:
        q = q.filter(Task.completed == completed)
    if importance:
        q = q.filter(Task.importance == importance)
    if time_horizon:
        q = q.filter(Task.time_horizon == time_horizon)
    if search:
        q = q.filter(Task.detail.ilike(f"%{search}%"))
    tasks = q.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    if tag:
        tasks = [t for t in tasks if t.tags and tag in t.tags]
    return tasks


def create_task(db: Session, task: TaskCreate, user_id: int) -> Task:
    db_task = Task(
        user_id=user_id,
        detail=task.detail,
        due_date=task.due_date,
        frequency=task.frequency,
        comments=task.comments,
        importance=task.importance,
        time_horizon=task.time_horizon,
        tags=task.tags,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task_id: int, task: TaskUpdate, user_id: int) -> Optional[Task]:
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return None
    data = task.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(db_task, k, v)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int, user_id: int) -> bool:
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True


def get_task_counts(db: Session, user_id: int) -> dict:
    total = db.query(Task).filter(Task.user_id == user_id).count()
    completed = db.query(Task).filter(Task.user_id == user_id, Task.completed == True).count()
    return {"total": total, "completed": completed}


def is_deadline_risk(due_date: Optional[date], days_threshold: int = 7) -> bool:
    if not due_date:
        return False
    return due_date <= date.today() + timedelta(days=days_threshold)


# Schedule (Phase 4, user-scoped)
def get_schedule_inputs(db: Session, user_id: int) -> List[UserScheduleInput]:
    return db.query(UserScheduleInput).filter(UserScheduleInput.user_id == user_id).order_by(UserScheduleInput.day_of_week).all()


def set_schedule_input(db: Session, user_id: int, day_of_week: int, user_description: Optional[str]) -> UserScheduleInput:
    row = db.query(UserScheduleInput).filter(
        UserScheduleInput.user_id == user_id,
        UserScheduleInput.day_of_week == day_of_week,
    ).first()
    if row:
        row.user_description = user_description
        db.commit()
        db.refresh(row)
        return row
    row = UserScheduleInput(user_id=user_id, day_of_week=day_of_week, user_description=user_description)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_schedule_blocks(db: Session, user_id: int) -> List[ScheduleBlock]:
    return db.query(ScheduleBlock).filter(ScheduleBlock.user_id == user_id).order_by(ScheduleBlock.day_of_week, ScheduleBlock.start_time).all()


def replace_schedule_blocks(db: Session, user_id: int, blocks: List[dict]) -> List[ScheduleBlock]:
    db.query(ScheduleBlock).filter(ScheduleBlock.user_id == user_id).delete()
    for b in blocks:
        db.add(ScheduleBlock(
            user_id=user_id,
            day_of_week=b["day_of_week"],
            start_time=b["start_time"],
            end_time=b["end_time"],
            label=b["label"],
            notes=b.get("notes"),
            is_active=True,
        ))
    db.commit()
    return get_schedule_blocks(db, user_id)


# Day log: what I did on a calendar date (persisted memory, user-scoped)
def get_day_log(db: Session, user_id: int, log_date: date) -> Optional[DayLog]:
    return db.query(DayLog).filter(DayLog.user_id == user_id, DayLog.date == log_date).first()


def set_day_log(db: Session, user_id: int, log_date: date, content: Optional[str]) -> DayLog:
    row = db.query(DayLog).filter(DayLog.user_id == user_id, DayLog.date == log_date).first()
    if row:
        row.content = content
        db.commit()
        db.refresh(row)
        return row
    row = DayLog(user_id=user_id, date=log_date, content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_day_logs_in_range(db: Session, user_id: int, start_date: date, end_date: date) -> List[DayLog]:
    return (
        db.query(DayLog)
        .filter(DayLog.user_id == user_id, DayLog.date >= start_date, DayLog.date <= end_date)
        .order_by(DayLog.date.asc())
        .all()
    )


def get_tasks_due_in_range(db: Session, user_id: int, start_date: date, end_date: date) -> List[Task]:
    return (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.completed == False,
            Task.due_date.isnot(None),
            Task.due_date >= start_date,
            Task.due_date <= end_date,
        )
        .order_by(Task.due_date.asc())
        .all()
    )
