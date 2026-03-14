"""
Prioritize: LLM assigns time_horizon, importance, complexity per task.

Mapping (LLM → UI):
- LLM returns: focus_today | focus_week_1 | focus_week_2 | focus_week_3 | focus_week_4 | focus_later
- Backend stores that value in task.time_horizon.
- API (TaskResponse) normalizes legacy on read only: focus_week→focus_week_1, focus_now→focus_today, focus_month→focus_week_2.
- Frontend utils.TIME_HORIZON_SECTIONS maps each horizon to a section label (Focus today, Focus week 1, …).
"""
import json
import logging
import re
from datetime import date
from typing import Any, Dict, List, Set

from .client import complete

logger = logging.getLogger(__name__)

VALID_TIME_HORIZONS = {
    "focus_today",
    "focus_week_1",
    "focus_week_2",
    "focus_week_3",
    "focus_week_4",
    "focus_later",
}
VALID_IMPORTANCE = {"P1", "P2", "P3"}
VALID_COMPLEXITY = {"small", "medium", "large"}


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
        "rank": getattr(task, "rank", None),
    }


def _build_prompt(tasks_summary: List[Dict]) -> str:
    tasks_json = json.dumps(tasks_summary, indent=2)
    today = date.today().isoformat()
    return f"""### Role
You are a High-Performance Executive Assistant specializing in Capacity Planning. You manage a strict **5-Point Weekly Velocity** (Large=3, Medium=2, Small=1).

**Today's date:** {today}
- Week 1 = days 0-6 from today, Week 2 = days 7-13, Week 3 = days 14-20, Week 4 = days 21-27.

### Step 1: Fixed Commitment Slotting (Tasks WITH Due Dates)
Calculate **Start Date** = Due Date minus Buffer (Large=30d, Medium=14d, Small=7d). Assign to the week that contains that Start Date:
- Start Date in Week 1 → use focus_today (if top 1-2 for today) or **focus_week_1**
- Start Date in Week 2 → **focus_week_2**
- Start Date in Week 3 → **focus_week_3**
- Start Date in Week 4 → **focus_week_4**
- Start Date after Week 4 or no due date and low priority → **focus_later**
You MUST use focus_week_2, focus_week_3, focus_week_4 when the Start Date falls in those weeks; do not put everything in focus_week_1.

### Step 2: Backlog Injection (Tasks WITHOUT Due Dates)
Fill the 5-point budget per week. Week 1 first (P1 then P2 by rank), then Week 2, 3, 4. Assign **focus_week_1**, **focus_week_2**, **focus_week_3**, or **focus_week_4** so tasks are spread across weeks. Never put all tasks in focus_week_1.

### Step 3: Horizon Definitions (use these exact strings)
- **focus_today:** Top 1-2 items for today only (max 5 points total for Week 1).
- **focus_week_1** / **focus_week_2** / **focus_week_3** / **focus_week_4:** Task belongs in that calendar week.
- **focus_later:** Does not fit in the next 4 weeks or P3 importance.

### Step 4: Cognitive Guardrails
- Max 5 complexity points per week. Risk (health/financial) → Week 1 (focus_today or focus_week_1).

### Output Format (Strict JSON Array)
- ONLY a JSON array of arrays. No markdown. No explanation.
- Format: [[task_id, time_horizon, importance, complexity]]
- time_horizon: exactly one of focus_today, focus_week_1, focus_week_2, focus_week_3, focus_week_4, focus_later
- Spread tasks across focus_week_1, focus_week_2, focus_week_3, focus_week_4 where appropriate.

Example: [[1, "focus_today", "P1", "small"], [2, "focus_week_1", "P2", "medium"], [3, "focus_week_2", "P1", "large"], [4, "focus_later", "P3", "small"]]

### Tasks to Process:
{tasks_json}"""


def _normalize_json_string(s: str) -> str:
    """Remove trailing commas and fix truncated JSON that LLMs sometimes emit."""
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    # Handle truncated response: ends with "," or ", " but no closing "]"
    s = re.sub(r",\s*$", "", s)
    if s.rstrip() and not s.rstrip().endswith("]"):
        s = s.rstrip()
        if s.startswith("["):
            s = s + "]"
    return s


def _parse_response(text: str, task_ids: Set[int]) -> List[Dict]:
    text = (text or "").strip()
    if not text:
        raise ValueError("LLM returned empty response. Try again or check the model is available.")
    # Try to extract JSON array (in case LLM wraps in markdown or adds prose)
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    # Normalize trailing commas and truncated arrays before parsing
    text = _normalize_json_string(text)
    logger.debug("Prioritize parse input (extracted array, length=%d): %s", len(text), text)
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
        # Compact format: [task_id, time_horizon, importance, complexity]
        if isinstance(item, list) and len(item) >= 4:
            tid, th, imp, complexity = item[0], item[1], item[2], item[3]
            tid = int(tid) if tid is not None else None
            complexity = (str(complexity).strip().lower() if complexity else None) or None
        elif isinstance(item, dict):
            tid = item.get("task_id")
            th = item.get("time_horizon")
            imp = item.get("importance")
            complexity = (item.get("complexity") or "").strip().lower() or None
        else:
            continue
        if tid is None or int(tid) not in task_ids:
            continue
        th = str(th).strip() if th is not None else "focus_later"
        imp = str(imp).strip() if imp is not None else "P2"
        if th not in VALID_TIME_HORIZONS:
            th = "focus_later"
        if imp not in VALID_IMPORTANCE:
            imp = "P2"
        if complexity not in VALID_COMPLEXITY:
            complexity = None
        result.append({"task_id": int(tid), "time_horizon": th, "importance": imp, "complexity": complexity})
    return result


def prioritize_tasks(tasks: list) -> List[Dict]:
    """Call LLM to get time_horizon, importance, and complexity per task. Returns list of { task_id, time_horizon, importance, complexity }."""
    if not tasks:
        return []
    summary = [_task_summary(t) for t in tasks]
    prompt = _build_prompt(summary)
    response = complete(prompt, json_mode=True, max_tokens=8192)
    logger.info("Prioritize LLM raw response (length=%d): %s", len(response), response)
    # Always print so it shows in Railway Deploy logs
    print(f"[Prioritize] LLM raw response (length={len(response)}): {response!r}", flush=True)
    task_ids = {t.id for t in tasks}
    return _parse_response(response, task_ids)
