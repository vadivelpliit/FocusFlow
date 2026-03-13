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
    return f"""### Role
You are a High-Performance Executive Assistant specializing in Cognitive Load Management. Your goal is to organize the user's backlog into a realistic, high-impact schedule.

### Step 1: Reality-Check Evaluation
Before assigning horizons, analyze each task's "True Urgency":
- **Domain Lead-Time:** Use your world knowledge. (e.g., Taxes, Medical Appointments, or Large Projects require 3-4 weeks of lead time). If the "Start Date" is now, treat it as urgent.
- **Risk Multiplier:** Any task tagged "health," "financial," or "legal" automatically jumps one priority level (P2 becomes P1) and moves closer in time horizon.
- **The "Rot" Factor:** For tasks with no due_date, assign a "Virtual Deadline" based on importance. High-importance items without dates MUST NOT stay in focus_later for more than 7 days.

### Step 2: The "Cognitive Budget" (Slot Filling)
You must distribute tasks to prevent burnout while ensuring progress.
- **Focus_Today Budget:** Max 1 "Large" task + 2 "Small" tasks, OR 3 "Medium" tasks. Total "Complexity" should not exceed a "5-point" limit (Large=3, Medium=2, Small=1).
- **The "Large" Progress Rule:** If a task is LARGE and due within 21 days, it MUST have a presence in focus_today or focus_week to ensure incremental progress.
- **The "Squeeze-In" Rule:** If the today/week buckets are full of Large tasks, prioritize adding a "Small" high-priority task rather than another Large one.

### Step 3: Horizon Definitions
1. focus_now/today: Immediate risks (financial/health), tasks starting today based on lead-time, or "Quick Wins" (Small complexity) to build momentum.
2. focus_week: Heavy lifting. Large projects requiring multiple days of effort.
3. focus_month: Preparatory tasks and medium-term milestones.
4. focus_later: Low-priority, low-risk, or "Someday" ideas.

### Output Requirements
- Respect existing 'importance' or 'complexity' if already set by the user.
- RETURN ONLY a valid JSON array of objects.
- Keys: task_id (number), time_horizon (string), importance (string), reasoning (string - a short 10-word explanation of why it was placed here).

Example: [{{"task_id": 1, "time_horizon": "focus_today", "importance": "P1", "reasoning": "Tax deadline in 2 weeks; financial risk."}}, ...]

### Tasks to Process:
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
        reasoning = (item.get("reasoning") or "").strip() or None
        if th not in VALID_TIME_HORIZONS:
            th = "focus_later"
        if imp not in VALID_IMPORTANCE:
            imp = "P2"
        result.append({"task_id": int(tid), "time_horizon": th, "importance": imp, "reasoning": reasoning})
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
