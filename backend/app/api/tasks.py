from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..crud import (
    create_task,
    delete_task,
    get_task,
    get_tasks,
    get_task_counts,
    update_task,
)
from ..database import get_db
from ..models import User
from ..schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _run_prioritize(db: Session, user_id: int):
    from ..llm.prioritize import prioritize_tasks
    from ..schemas import TaskUpdate

    tasks = get_tasks(db, user_id=user_id, completed=False)
    if not tasks:
        return 0
    # Call LLM once for all tasks
    results = prioritize_tasks(tasks)
    # Build lookup so we can respect existing manual settings
    by_id = {t.id: t for t in tasks}
    updated_count = 0
    for r in results:
        task = by_id.get(r["task_id"])
        if not task:
            continue
        # If user already set importance or time_horizon, do NOT change it.
        new_time_horizon = task.time_horizon if task.time_horizon is not None else r["time_horizon"]
        new_importance = task.importance if task.importance is not None else r["importance"]
        # Only write if something actually changes
        if new_time_horizon != task.time_horizon or new_importance != task.importance:
            update_task(
                db,
                r["task_id"],
                TaskUpdate(time_horizon=new_time_horizon, importance=new_importance),
                user_id=user_id,
            )
            updated_count += 1
    return updated_count


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    completed: Optional[bool] = Query(None),
    importance: Optional[str] = Query(None),
    time_horizon: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_tasks(db, user_id=current_user.id, completed=completed, importance=importance, time_horizon=time_horizon, tag=tag, search=search)


@router.get("/counts")
def task_counts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_task_counts(db, user_id=current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
def read_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskResponse, status_code=201)
def create_task_route(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_task(db, task, user_id=current_user.id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task_route(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    updated = update_task(db, task_id, task, user_id=current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{task_id}", status_code=204)
def delete_task_route(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not delete_task(db, task_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/prioritize")
def prioritize_tasks_route(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Run LLM to assign time_horizon and importance to all incomplete tasks."""
    try:
        updated = _run_prioritize(db, current_user.id)
        return {"updated": updated}
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail="AI prioritization is not configured. Set OPENAI_API_KEY.")
        raise HTTPException(status_code=422, detail=str(e))
