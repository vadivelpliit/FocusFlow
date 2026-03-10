export function isDeadlineRisk(dueDate: string | null, daysThreshold = 7): boolean {
  if (!dueDate) return false;
  const due = new Date(dueDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const limit = new Date(today);
  limit.setDate(limit.getDate() + daysThreshold);
  return due <= limit;
}

export const TIME_HORIZON_SECTIONS = [
  // What you see in the app: focus buckets
  { id: "focus_today", label: "Focus today", horizons: ["focus_now", "focus_today"] },
  { id: "focus_week", label: "Focus this week", horizons: ["focus_week"] },
  { id: "focus_month", label: "Focus this month", horizons: ["focus_month"] },
  { id: "focus_later", label: "Focus later", horizons: ["focus_later", ""] },
] as const;

export function getSectionForHorizon(horizon: string | null): string {
  if (!horizon) return "focus_later";
  const section = TIME_HORIZON_SECTIONS.find((s) => (s.horizons as readonly string[]).includes(horizon));
  return section?.id ?? "focus_later";
}
