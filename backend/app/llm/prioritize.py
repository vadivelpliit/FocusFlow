"""
Prioritize: LLM returns priority_score + complexity + reason; app logic assigns time_horizon.

Flow:
- LLM returns JSON array of { task_id, priority_score (1-100), complexity, reason }.
- We compute time_horizon: with due_date → buffer by complexity, map start_date to focus_today/week_1-4/later;
  without due_date → fill weekly 5-point budget by priority_score.
- Importance (P1/P2/P3) derived from priority_score. Stored: time_horizon, importance, complexity, reasoning.
"""
import json
import logging
import re
import time
from datetime import date, timedelta
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

COMPLEXITY_BUFFER_DAYS = {"small": 7, "medium": 14, "large": 30}
COMPLEXITY_POINTS = {"small": 1, "medium": 2, "large": 3}
WEEKLY_POINT_BUDGET = 5


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
You are an expert Prioritization Engine. Your task is to analyze a list of tasks and assign a "Strategic Priority Score" (1-100).

### Instructions
1. For each task, output a JSON object with:
   - "task_id": The ID provided.
   - "priority_score": An integer (1-100) based on impact, urgency, and risk.
   - "complexity": If missing or null, infer it as "small", "medium", or "large" based on the task detail.
   - "reason": A one-sentence executive justification.

2. Prioritize:
   - Financial/Legal/Health risks = Score 80-100.
   - Blockers for other projects = Score 70-90.
   - High-impact/Long-term alignment = Score 60-80.
   - All others = Score 1-59.

### Format
Return ONLY a JSON array of these objects. No markdown, no conversational text.

### Data
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


def _score_to_importance(score: int) -> str:
    if score >= 80:
        return "P1"
    if score >= 50:
        return "P2"
    return "P3"


def _parse_llm_response(text: str, task_ids: Set[int]) -> List[Dict]:
    """Parse LLM JSON array of { task_id, priority_score, complexity, reason }."""
    text = (text or "").strip()
    if not text:
        raise ValueError("LLM returned empty response. Try again or check the model is available.")
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    text = _normalize_json_string(text)
    logger.debug("Prioritize parse input (length=%d): %s", len(text), text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = json.loads(_normalize_json_string(text))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM response was not valid JSON: {e}. Try again."
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
        tid = int(tid)
        try:
            score = int(item.get("priority_score", 50))
        except (TypeError, ValueError):
            score = 50
        score = max(1, min(100, score))
        complexity = (item.get("complexity") or "").strip().lower() or None
        if complexity not in VALID_COMPLEXITY:
            complexity = "medium"
        reason = (item.get("reason") or "").strip() or None
        result.append({
            "task_id": tid,
            "priority_score": score,
            "complexity": complexity,
            "reason": reason,
        })
    return result


def _compute_horizons(tasks: List[Any], llm_results: List[Dict]) -> List[Dict]:
    """
    Compute time_horizon for each task from LLM priority_score + complexity.
    - With due_date: start_date = due_date - buffer[complexity]; map to focus_today / focus_week_1..4 / focus_later.
    - Without due_date: fill weekly 5-point budget by priority_score (high score first).
    """
    today = date.today()
    by_id = {t.id: t for t in tasks}
    llm_by_id = {r["task_id"]: r for r in llm_results}

    out: List[Dict] = []
    no_due: List[tuple] = []  # (task_id, priority_score, points)

    for r in llm_results:
        tid = r["task_id"]
        task = by_id.get(tid)
        if not task:
            continue
        score = r["priority_score"]
        complexity = r.get("complexity") or "medium"
        points = COMPLEXITY_POINTS.get(complexity, 2)
        importance = _score_to_importance(score)

        if getattr(task, "due_date", None):
            due = task.due_date
            if hasattr(due, "date"):
                due = due.date()
            buffer_days = COMPLEXITY_BUFFER_DAYS.get(complexity, 14)
            start_date = due - timedelta(days=buffer_days)
            if start_date <= today:
                time_horizon = "focus_today"
            else:
                delta = (start_date - today).days
                if delta <= 7:
                    time_horizon = "focus_week_1"
                elif delta <= 14:
                    time_horizon = "focus_week_2"
                elif delta <= 21:
                    time_horizon = "focus_week_3"
                elif delta <= 28:
                    time_horizon = "focus_week_4"
                else:
                    time_horizon = "focus_later"
        else:
            no_due.append((tid, score, points))

        if getattr(task, "due_date", None):
            out.append({
                "task_id": tid,
                "time_horizon": time_horizon,
                "importance": importance,
                "complexity": complexity,
                "reasoning": r.get("reason"),
            })

    # No-due-date: fill week 1..4 by 5 points each, sorted by priority_score desc
    no_due.sort(key=lambda x: -x[1])
    week_budgets = [
        ("focus_week_1", WEEKLY_POINT_BUDGET),
        ("focus_week_2", WEEKLY_POINT_BUDGET),
        ("focus_week_3", WEEKLY_POINT_BUDGET),
        ("focus_week_4", WEEKLY_POINT_BUDGET),
    ]
    week_idx = 0
    for tid, score, points in no_due:
        importance = _score_to_importance(score)
        r = llm_by_id[tid]
        complexity = r.get("complexity") or "medium"
        # Skip weeks that don't have room for this task
        while week_idx < len(week_budgets) and week_budgets[week_idx][1] < points:
            week_idx += 1
        if week_idx < len(week_budgets):
            name, budget = week_budgets[week_idx]
            time_horizon = name
            week_budgets[week_idx] = (name, budget - points)
            if week_budgets[week_idx][1] <= 0:
                week_idx += 1
        else:
            time_horizon = "focus_later"
        out.append({
            "task_id": tid,
            "time_horizon": time_horizon,
            "importance": importance,
            "complexity": complexity,
            "reasoning": r.get("reason"),
        })

    return out


def prioritize_tasks(tasks: list) -> List[Dict]:
    """
    LLM returns priority_score + complexity + reason; we compute time_horizon.
    Returns list of { task_id, time_horizon, importance, complexity, reasoning }.
    """
    if not tasks:
        return []
    summary = [_task_summary(t) for t in tasks]
    prompt = _build_prompt(summary)
    t0 = time.perf_counter()
    response = complete(prompt, json_mode=True, max_tokens=8192)
    elapsed = time.perf_counter() - t0
    logger.info("Prioritize LLM raw response (length=%d, %.2fs): %s", len(response), elapsed, response)
    print(f"[Prioritize] LLM responded in {elapsed:.2f}s (length={len(response)}): {response!r}", flush=True)
    task_ids = {t.id for t in tasks}
    llm_results = _parse_llm_response(response, task_ids)
    return _compute_horizons(tasks, llm_results)
