import json
import re
from typing import Any, Dict, List


from .client import complete

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def propose_schedule(
    day_descriptions: List[str],
    desired_activities: List[str],
) -> List[Dict[str, Any]]:
    """
    day_descriptions: 7 strings, index 0 = Monday ... 6 = Sunday (what user currently does).
    desired_activities: e.g. ["office", "exercise", "cook", "admin"]
    Returns list of { day_of_week (0-6), start_time, end_time, label }.
    """
    lines = []
    for i, name in enumerate(DAY_NAMES):
        desc = (day_descriptions[i] or "").strip() or "(not described)"
        lines.append(f"{name} (day_of_week={i}): {desc}")
    current_week = "\n".join(lines)
    activities = ", ".join(desired_activities) if desired_activities else "general productivity"

    prompt = f"""You are a schedule planning assistant. The user has described what they currently do each day and what activities they want to fit in.

Current week (what they do now):
{current_week}

Desired activities to include: {activities}

Propose a realistic 7-day weekly schedule with time blocks. Use day_of_week 0=Monday through 6=Sunday.
Return ONLY a JSON array of objects. Each object must have: day_of_week (number 0-6), start_time (e.g. "07:00"), end_time (e.g. "08:00"), label (short activity name).
Use 24-hour format for times. Typical block length 30-120 minutes. Cover morning to evening (e.g. 5am to 10pm).
Example: [{{"day_of_week": 0, "start_time": "06:00", "end_time": "07:00", "label": "Exercise"}}, ...]

JSON array:"""

    response = complete(prompt, max_tokens=3000)
    return _parse_schedule_response(response)


def _parse_schedule_response(text: str) -> List[Dict[str, Any]]:
    text = text.strip()
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    data = json.loads(text)
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            dow = int(item.get("day_of_week", 0))
            if dow < 0 or dow > 6:
                continue
            start = str(item.get("start_time", "09:00"))[:5]
            end = str(item.get("end_time", "10:00"))[:5]
            label = str(item.get("label", "Activity"))[:200]
            result.append({
                "day_of_week": dow,
                "start_time": start,
                "end_time": end,
                "label": label,
                "notes": item.get("notes"),
            })
        except (TypeError, ValueError):
            continue
    return result
