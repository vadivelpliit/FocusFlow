from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Task, ScheduleBlock, UserScheduleInput, DayLog
from .schemas import TaskCreate, TaskUpdate


def get_task(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()


def get_tasks(
    db: Session,
    completed: Optional[bool] = None,
    importance: Optional[str] = None,
    time_horizon: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Task]:
    q = db.query(Task)
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


def create_task(db: Session, task: TaskCreate) -> Task:
    db_task = Task(
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


def update_task(db: Session, task_id: int, task: TaskUpdate) -> Optional[Task]:
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    data = task.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(db_task, k, v)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> bool:
    db_task = get_task(db, task_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True


def get_task_counts(db: Session) -> dict:
    total = db.query(Task).count()
    completed = db.query(Task).filter(Task.completed == True).count()
    return {"total": total, "completed": completed}


def is_deadline_risk(due_date: Optional[date], days_threshold: int = 7) -> bool:
    if not due_date:
        return False
    return due_date <= date.today() + timedelta(days=days_threshold)


# Schedule (Phase 4)
def get_schedule_inputs(db: Session) -> List[UserScheduleInput]:
    return db.query(UserScheduleInput).order_by(UserScheduleInput.day_of_week).all()


def set_schedule_input(db: Session, day_of_week: int, user_description: Optional[str]) -> UserScheduleInput:
    row = db.query(UserScheduleInput).filter(UserScheduleInput.day_of_week == day_of_week).first()
    if row:
        row.user_description = user_description
        db.commit()
        db.refresh(row)
        return row
    row = UserScheduleInput(day_of_week=day_of_week, user_description=user_description)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_schedule_blocks(db: Session) -> List[ScheduleBlock]:
    return db.query(ScheduleBlock).order_by(ScheduleBlock.day_of_week, ScheduleBlock.start_time).all()


def replace_schedule_blocks(db: Session, blocks: List[dict]) -> List[ScheduleBlock]:
    db.query(ScheduleBlock).delete()
    for b in blocks:
        db.add(ScheduleBlock(
            day_of_week=b["day_of_week"],
            start_time=b["start_time"],
            end_time=b["end_time"],
            label=b["label"],
            notes=b.get("notes"),
            is_active=True,
        ))
    db.commit()
    return get_schedule_blocks(db)


# Day log: what I did on a calendar date (persisted memory)
def get_day_log(db: Session, log_date: date) -> Optional[DayLog]:
    return db.query(DayLog).filter(DayLog.date == log_date).first()


def set_day_log(db: Session, log_date: date, content: Optional[str]) -> DayLog:
    row = db.query(DayLog).filter(DayLog.date == log_date).first()
    if row:
        row.content = content
        db.commit()
        db.refresh(row)
        return row
    row = DayLog(date=log_date, content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_day_logs_in_range(db: Session, start_date: date, end_date: date) -> List[DayLog]:
    return (
        db.query(DayLog)
        .filter(DayLog.date >= start_date, DayLog.date <= end_date)
        .order_by(DayLog.date.asc())
        .all()
    )


def get_tasks_due_in_range(db: Session, start_date: date, end_date: date) -> List[Task]:
    return (
        db.query(Task)
        .filter(Task.completed == False, Task.due_date.isnot(None), Task.due_date >= start_date, Task.due_date <= end_date)
        .order_by(Task.due_date.asc())
        .all()
    )
