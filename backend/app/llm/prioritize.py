import json
import logging
import re
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
    return f"""### Role
You are a High-Performance Executive Assistant specializing in Capacity Planning. You manage a strict **5-Point Weekly Velocity** (Large=3, Medium=2, Small=1).

### Step 1: Fixed Commitment Slotting (Tasks WITH Due Dates)
Calculate the **Start Date** (Due Date minus Buffer: Large=30d, Medium=14d, Small=7d).
- Assign these to the earliest applicable week (Week 1, 2, 3, or 4) based on the Start Date.
- These tasks take priority in the 5-point budget.

### Step 2: Backlog Injection (Tasks WITHOUT Due Dates)
For all items without a due date, use their **Rank (1-5)** and **Importance (P1-P3)**:
- Look for "Open Slots" in the 5-point budget for Week 1.
- Fill slots in order: P1 (Rank 1 -> 5), then P2 (Rank 1 -> 5).
- If Week 1 is full, move to Week 2, and so on.

### Step 3: Horizon Definitions
1. **focus_today:** The top 1-2 items from Week 1 (Total max 5 points for the week).
2. **focus_week_1 / focus_week_2 / focus_week_3 / focus_week_4:** Tasks assigned to these specific 7-day windows.
3. **focus_later:** Anything that doesn't fit in the next 4 weeks or has P3 importance.

### Step 4: Cognitive Guardrails
- **Max Points:** Never exceed 5 points in any single week bucket.
- **Risk Multiplier:** Health/Financial tasks bypass the budget and go to Week 1 immediately.

### Inputs to Use
For each task use: detail, comments, due_date, tags, importance (P1/P2/P3), complexity (small/medium/large), and rank (1-5 when present). If importance or complexity is missing, infer it from the task (e.g. first-time US tax = large; quick call = small).

### Output Format (Strict JSON Array)
- Reply with ONLY a JSON array of arrays. No markdown, no explanation.
- Format: [[task_id, time_horizon, importance, complexity]]
- time_horizon: one of focus_today, focus_week_1, focus_week_2, focus_week_3, focus_week_4, focus_later
- importance: P1, P2, or P3
- complexity: small, medium, or large
- One row per task. Keep responses short to avoid truncation.

Example: [[7, "focus_week_2", "P1", "large"], [8, "focus_today", "P1", "small"]]

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
