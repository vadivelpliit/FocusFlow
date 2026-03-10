import json
import re
from typing import Any, Dict, List, Set

from .client import complete

VALID_TIME_HORIZONS = {"focus_now", "focus_today", "focus_week", "focus_month", "focus_later"}
VALID_IMPORTANCE = {"P1", "P2", "P3"}


def _task_summary(task: Any) -> dict:
    return {
        "task_id": task.id,
        "detail": task.detail,
        "due_date": str(task.due_date) if task.due_date else None,
        "frequency": task.frequency,
        "comments": (task.comments or "")[:300],
        "tags": task.tags or [],
        "complexity": getattr(task, "complexity", None),
    }


def _build_prompt(tasks_summary: List[Dict]) -> str:
    tasks_json = json.dumps(tasks_summary, indent=2)
    return f"""You are a task prioritization assistant. Given a list of tasks, assign each task:
1. time_horizon (Focus): one of focus_now, focus_today, focus_week, focus_month, focus_later
   - focus_now / focus_today: overdue or due very soon, or critical (e.g. financial/legal risk)
   - focus_week: should be worked on this week
   - focus_month: should be moved forward this month
   - focus_later: no urgency (someday)
2. importance (Priority / consequence): P1 (highest), P2 (medium), P3 (lower). Consider: financial impact if delayed, deadlines, how many steps (comments), and tags like "financial" or "urgent".
3. complexity: small / medium / large (provided as "complexity"). For LARGE tasks with a deadline this month or next month, DO NOT leave them in focus_later until the last moment. Make sure they appear in focus_week or focus_today early enough that the user can make progress over multiple days.

Return ONLY a valid JSON array of objects, one per task, with keys: task_id (number), time_horizon (string), importance (string).
Example: [{{"task_id": 1, "time_horizon": "focus_today", "importance": "P1"}}, ...]

Tasks:
{tasks_json}"""


def _parse_response(text: str, task_ids: Set[int]) -> List[Dict]:
    text = text.strip()
    # Try to extract JSON array (in case LLM wraps in markdown)
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array")
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        tid = item.get("task_id")
        if tid is None or int(tid) not in task_ids:
            continue
        th = item.get("time_horizon")
        imp = item.get("importance")
        if th not in VALID_TIME_HORIZONS:
            th = "focus_later"
        if imp not in VALID_IMPORTANCE:
            imp = "P2"
        result.append({"task_id": int(tid), "time_horizon": th, "importance": imp})
    return result


def prioritize_tasks(tasks: list) -> List[Dict]:
    """Call LLM to get time_horizon and importance for each task. Returns list of { task_id, time_horizon, importance }."""
    if not tasks:
        return []
    summary = [_task_summary(t) for t in tasks]
    prompt = _build_prompt(summary)
    response = complete(prompt)
    task_ids = {t.id for t in tasks}
    return _parse_response(response, task_ids)
