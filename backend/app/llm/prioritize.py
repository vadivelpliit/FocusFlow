import json
import logging
import re
from typing import Any, Dict, List, Set

from .client import complete

logger = logging.getLogger(__name__)

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
        "importance": getattr(task, "importance", None),
        "complexity": getattr(task, "complexity", None),
    }


def _build_prompt(tasks_summary: List[Dict]) -> str:
    tasks_json = json.dumps(tasks_summary, indent=2)
    return f"""### Role
You are a High-Performance Executive Assistant specializing in Cognitive Load Management. Your goal is to organize the user's backlog into a realistic, high-impact schedule.

### Inputs to Use
For each task, use: "detail" (what the task is), "comments" (next steps, progress notes, or context the user added), and—when present—"importance" (P1/P2/P3) and "complexity" (small/medium/large). Detail and comments tell you what the task is and where the user stands; importance and complexity, when set, should inform your time_horizon and reasoning. Use all of these to decide time_horizon, importance, and reasoning.

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
- Reply with ONLY a valid JSON array of objects. No markdown, no code fences, no explanation before or after.
- Keys: task_id (number), time_horizon (string), importance (string), reasoning (string - a short phrase, no double quotes inside).
- Use valid JSON only: no trailing commas after last element, no unescaped quotes inside strings.

Example: [{{"task_id": 1, "time_horizon": "focus_today", "importance": "P1", "reasoning": "Tax deadline in 2 weeks"}}, ...]

### Tasks to Process:
{tasks_json}"""


def _normalize_json_string(s: str) -> str:
    """Remove trailing commas and other common invalid JSON that LLMs sometimes emit."""
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    return s


def _parse_response(text: str, task_ids: Set[int]) -> List[Dict]:
    text = (text or "").strip()
    if not text:
        raise ValueError("LLM returned empty response. Try again or check the model is available.")
    # Try to extract JSON array (in case LLM wraps in markdown or adds prose)
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    logger.debug("Prioritize parse input (extracted array, length=%d): %s", len(text), text)
    # Try parsing; if it fails, try again after removing trailing commas
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = json.loads(_normalize_json_string(text))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM response was not valid JSON: {e}. "
                "The model may have returned plain text or an error. Try again."
            ) from e
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
    response = complete(prompt, json_mode=True)
    logger.info("Prioritize LLM raw response (length=%d): %s", len(response), response)
    task_ids = {t.id for t in tasks}
    return _parse_response(response, task_ids)
