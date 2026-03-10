import json
from typing import Any, Dict, List

from .client import complete


def _task_summary(task: Any) -> Dict:
    return {
        "id": task.id,
        "detail": task.detail,
        "due_date": str(task.due_date) if task.due_date else None,
        "importance": task.importance,
        "time_horizon": task.time_horizon,
        "comments": (task.comments or "")[:200],
        "tags": task.tags or [],
    }


def chat_reply(user_message: str, tasks: List[Any]) -> str:
    """Return an LLM reply suggesting what to do based on user context and tasks."""
    tasks_data = [_task_summary(t) for t in tasks]
    tasks_json = json.dumps(tasks_data, indent=2)

    prompt = f"""You are a helpful task assistant for an app where each task has a current priority:
- time_horizon: focus_today, focus_week, focus_month, or focus_later (these show as Focus today / this week / this month / later)
- importance: P1 (highest), P2, or P3

The user can change a task's Focus via the 3-dots menu on that task (e.g. Move to Focus today / Focus this week / Focus later).

Rules:
1. If the user asks "why is [X] not prioritized?" or "why isn't [X] in Focus today?" or "why is [X] in Focus later?" — explain why that task has its CURRENT assignment (e.g. no due date, far deadline, or the AI prioritization put it there). Then say they can move it using the task's 3-dots menu (e.g. "Move to Focus today" or "Move to Focus this week") if they want it higher. Do NOT give generic tips like "schedule an appointment" or "set a reminder"; answer the "why" about the app's priority.
2. If they ask "what's at risk?", highlight tasks with near deadlines or financial impact.
3. If they ask to "batch" tasks, group similar ones.
4. If they ask what to do today / with 30 min, suggest 2-4 concrete tasks from the list with brief reasons.
5. Be concise. Reply in plain text; no JSON or markdown lists unless brief.

User message: {user_message}

Their incomplete tasks (each has id, detail, due_date, importance, time_horizon, comments, tags):
{tasks_json}

Your reply:"""

    return complete(prompt, max_tokens=800)
