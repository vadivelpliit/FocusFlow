"use client";

import { useState, useEffect, useRef } from "react";
import type { Task } from "@/lib/api";
import { isDeadlineRisk } from "@/lib/utils";
import styles from "./TaskRow.module.css";

const MOVE_OPTIONS: { label: string; time_horizon: string }[] = [
  { label: "Move to Focus today", time_horizon: "focus_today" },
  { label: "Move to Focus this week", time_horizon: "focus_week" },
  { label: "Move to Focus later", time_horizon: "focus_later" },
];

const SECTION_LABELS: Record<string, string> = {
  focus_now: "Focus today",
  focus_today: "Focus today",
  focus_week: "Focus this week",
  focus_month: "Focus this month",
  focus_later: "Focus later",
};
function sectionLabel(timeHorizon: string | null): string {
  return (timeHorizon && SECTION_LABELS[timeHorizon]) || "Focus later";
}

interface TaskRowProps {
  task: Task;
  onToggleComplete: (id: number, completed: boolean) => void;
  onUpdate: (id: number, updates: Partial<Task>) => void;
  onDelete: (id: number) => void;
}

export function TaskRow({ task, onToggleComplete, onUpdate, onDelete }: TaskRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [detail, setDetail] = useState(task.detail);
  const [comments, setComments] = useState(task.comments || "");
  const [dueDate, setDueDate] = useState(task.due_date || "");
  const [importance, setImportance] = useState(task.importance || "");
  const [timeHorizon, setTimeHorizon] = useState(task.time_horizon || "");
  const [complexity, setComplexity] = useState(task.complexity || "");
  const deadlineRisk = isDeadlineRisk(task.due_date);

  useEffect(() => {
    setDetail(task.detail);
    setComments(task.comments || "");
    setDueDate(task.due_date || "");
    setImportance(task.importance || "");
    setTimeHorizon(task.time_horizon || "");
    setComplexity(task.complexity || "");
  }, [task.detail, task.comments, task.due_date, task.importance, task.time_horizon, task.complexity]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    if (menuOpen) document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [menuOpen]);

  const handleSave = () => {
    onUpdate(task.id, {
      detail: detail.trim() || task.detail,
      comments: comments.trim() || null,
      due_date: dueDate || null,
      importance: importance || null,
      time_horizon: timeHorizon || null,
      complexity: complexity || null,
    });
    setEditing(false);
  };

  const handleMoveTo = (time_horizon: string) => {
    onUpdate(task.id, { time_horizon });
    setMenuOpen(false);
  };

  return (
    <div className={`${styles.row} ${task.completed ? styles.completed : ""} ${deadlineRisk ? styles.deadlineRisk : ""}`}>
      <div className={styles.main}>
        <button
          type="button"
          className={styles.checkbox}
          onClick={() => onToggleComplete(task.id, !task.completed)}
          aria-label={task.completed ? "Mark incomplete" : "Mark complete"}
        >
          {task.completed ? "✓" : ""}
        </button>
        <div className={styles.content}>
          <span className={styles.detail}>{task.detail}</span>
          <div className={styles.meta}>
            {(task.tags || []).map((tag) => (
              <span key={tag} className={`${styles.tag} ${styles[`tag_${tag}`] || styles.tagDefault}`}>
                {tag}
              </span>
            ))}
            {task.importance && (
              <span className={styles.pill}>{task.importance}</span>
            )}
            {task.complexity && (
              <span className={styles.pill}>{task.complexity}</span>
            )}
            {deadlineRisk && (
              <span className={styles.deadlineBadge}>DEADLINE RISK</span>
            )}
          </div>
        </div>
        <div className={styles.rowActions} ref={menuRef}>
          <button
            type="button"
            className={styles.menuBtn}
            onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
            aria-label="Priority menu"
            aria-expanded={menuOpen}
          >
            ⋮
          </button>
          {menuOpen && (
            <div className={styles.menu}>
              {MOVE_OPTIONS.map((opt) => (
                <button
                  key={opt.time_horizon}
                  type="button"
                  className={styles.menuItem}
                  onClick={() => handleMoveTo(opt.time_horizon)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
          <button
            type="button"
            className={styles.expand}
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {expanded ? "▲" : "▼"}
          </button>
        </div>
      </div>
      {expanded && (
        <div className={styles.expanded}>
          {editing ? (
            <>
              <label className={styles.field}>
                Task
                <input
                  value={detail}
                  onChange={(e) => setDetail(e.target.value)}
                  className={styles.input}
                />
              </label>
              <label className={styles.field}>
                Due date
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className={styles.input}
                  />
                  <button
                    type="button"
                    className={styles.btnSecondary}
                    onClick={() => setDueDate("")}
                  >
                    Clear
                  </button>
                </div>
              </label>
              <label className={styles.field}>
                Frequency
                <select
                  value={task.frequency}
                  onChange={(e) => onUpdate(task.id, { frequency: e.target.value })}
                  className={styles.input}
                >
                  <option value="once">Once</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </label>
              <label className={styles.field}>
                Priority / consequence (P1 high, P2 medium, P3 low)
                <select
                  value={importance}
                  onChange={(e) => setImportance(e.target.value)}
                  className={styles.input}
                >
                  <option value="">—</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                  <option value="P3">P3</option>
                </select>
              </label>
              <label className={styles.field}>
                Complexity
                <select
                  value={complexity}
                  onChange={(e) => setComplexity(e.target.value)}
                  className={styles.input}
                >
                  <option value="">—</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large</option>
                </select>
              </label>
              <label className={styles.field}>
                Focus (section)
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select
                    value={timeHorizon}
                    onChange={(e) => setTimeHorizon(e.target.value)}
                    className={styles.input}
                  >
                    <option value="">Let AI decide</option>
                    <option value="focus_today">Focus today</option>
                    <option value="focus_week">Focus this week</option>
                    <option value="focus_month">Focus this month</option>
                    <option value="focus_later">Focus later</option>
                  </select>
                  <button
                    type="button"
                    className={styles.btnSecondary}
                    onClick={() => setTimeHorizon("")}
                  >
                    Clear
                  </button>
                </div>
              </label>
              <label className={styles.field}>
                Comments / Next steps
                <textarea
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className={styles.textarea}
                  rows={3}
                />
              </label>
              <div className={styles.actions}>
                <button type="button" className={styles.btnPrimary} onClick={handleSave}>
                  Save
                </button>
                <button type="button" className={styles.btnSecondary} onClick={() => setEditing(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className={styles.btnDanger}
                  onClick={() => {
                    if (confirm("Delete this task?")) onDelete(task.id);
                  }}
                >
                  Delete
                </button>
              </div>
            </>
          ) : (
            <>
              <div className={styles.info}>
                <span><strong>Due:</strong> {task.due_date || "—"}</span>
                <span><strong>Frequency:</strong> {task.frequency}</span>
                {task.importance && <span><strong>Priority:</strong> {task.importance}</span>}
                <span><strong>Section:</strong> {sectionLabel(task.time_horizon)}</span>
              </div>
              {task.comments && (
                <div className={styles.comments}>
                  <strong>Next steps:</strong>
                  <pre>{task.comments}</pre>
                </div>
              )}
              <button type="button" className={styles.btnSecondary} onClick={() => setEditing(true)}>
                Edit
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
