"""
AI recommends a plan for the rest of this week + next week, learning from
past "what I did" day logs. One-off activities are ignored; patterns are
incorporated so the plan converges with what the user actually does.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

from .client import complete


def _week_range(anchor: date) -> Tuple[date, date]:
    """Rest of week containing anchor (from anchor onward) + next full week."""
    # anchor's weekday: 0=Monday, 6=Sunday
    weekday = anchor.weekday()
    # End of "this week" = next Sunday
    days_to_sunday = 6 - weekday
    end_this_week = anchor + timedelta(days=days_to_sunday)
    start_next_week = end_this_week + timedelta(days=1)
    end_next_week = start_next_week + timedelta(days=6)
    return anchor, end_next_week


def recommend_plan(
    anchor_date: date,
    past_day_logs: List[Dict],
    schedule_blocks: List[Any],
    tasks_due: List[Any],
) -> str:
    """
    Generate a recommended plan for anchor_date through end of next week.
    past_day_logs: list of { "date": "YYYY-MM-DD", "content": "..." } (e.g. last 30 days).
    """
    start, end = _week_range(anchor_date)
    start_s = start.isoformat()
    end_s = end.isoformat()

    past_text = "\n".join(
        f"{d['date']}: {d['content']}" for d in past_day_logs if d.get("content")
    ) or "(No past logs yet.)"

    blocks_text = ""
    if schedule_blocks:
        by_dow = {}
        for b in schedule_blocks:
            by_dow.setdefault(b.day_of_week, []).append(f"  {b.start_time}-{b.end_time} {b.label}")
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for dow in range(7):
            if dow in by_dow:
                blocks_text += f"{day_names[dow]}: " + "\n".join(by_dow[dow]) + "\n"
    else:
        blocks_text = "(No recurring schedule yet.)"

    tasks_text = ""
    if tasks_due:
        tasks_text = "\n".join(
            f"- {t.detail} (due {t.due_date})" for t in tasks_due
        )
    else:
        tasks_text = "(No tasks due in this window.)"

    prompt = f"""You are a schedule assistant. The user has a calendar where they log "what I did" each day. Over time, your recommended plan should align more with what they actually do.

Given:
1) Past "what I did" entries (date + content). Look for PATTERNS (e.g. "exercise on Mon/Wed/Fri", "office on weekdays"). Ignore one-off events. If something repeats, incorporate it into the recommendation.
2) Their recurring schedule template (if any) — use as baseline.
3) Tasks with due dates in the window — slot them in where reasonable.

Output a recommended plan for {start_s} through {end_s}: rest of this week and next full week. Be concrete: time blocks or a clear daily outline. Write in plain text, 1-2 paragraphs or a short bullet list per day. The goal is that as they keep logging "what I did", your future recommendations will gradually match their real behavior; so base your suggestion on the patterns you see in their past logs and their template.

Past "what I did" (recent days):
{past_text}

Recurring schedule template:
{blocks_text}

Tasks due in this window:
{tasks_text}

Recommended plan:"""

    return complete(prompt, max_tokens=1500)


def get_recommend_window(anchor_date: date) -> Tuple[date, date]:
    """Return (start_date, end_date) for the recommendation window."""
    return _week_range(anchor_date)
