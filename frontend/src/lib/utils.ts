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
  { id: "urgent", label: "Urgent", horizons: ["focus_now", "focus_today"] },
  { id: "important", label: "Important", horizons: ["focus_week", "focus_month"] },
  { id: "someday", label: "Someday", horizons: ["focus_later"] },
] as const;

export function getSectionForHorizon(horizon: string | null): string {
  if (!horizon) return "someday";
  const section = TIME_HORIZON_SECTIONS.find((s) => (s.horizons as readonly string[]).includes(horizon));
  return section?.id ?? "someday";
}
