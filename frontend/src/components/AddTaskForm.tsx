"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { TaskCreate } from "@/lib/api";
import styles from "./AddTaskForm.module.css";

interface AddTaskFormProps {
  onCreated: () => void;
  onCancel: () => void;
}

const FREQUENCIES = ["once", "daily", "weekly", "monthly"];
const SUGGESTED_TAGS = ["financial", "call", "health", "paperwork", "immigration", "home", "project", "family", "urgent"];

export function AddTaskForm({ onCreated, onCancel }: AddTaskFormProps) {
  const [detail, setDetail] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [frequency, setFrequency] = useState("once");
  const [comments, setComments] = useState("");
  const [importance, setImportance] = useState<string>("");
  const [timeHorizon, setTimeHorizon] = useState<string>("");
  const [tags, setTags] = useState<string[]>([]);
  const [customTag, setCustomTag] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleTag = (tag: string) => {
    setTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  };

  const addCustomTag = () => {
    const t = customTag.trim().toLowerCase();
    if (t && !tags.includes(t)) {
      setTags((prev) => [...prev, t]);
      setCustomTag("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const payload: TaskCreate = {
        detail: detail.trim(),
        due_date: dueDate || null,
        frequency,
        comments: comments.trim() || null,
        tags: tags.length ? tags : null,
      };
      if (importance) payload.importance = importance;
      if (timeHorizon) payload.time_horizon = timeHorizon;
      await api.createTask(payload);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <h3 className={styles.title}>New task</h3>
      <label className={styles.label}>
        Task detail *
        <input
          value={detail}
          onChange={(e) => setDetail(e.target.value)}
          className={styles.input}
          placeholder="e.g. Recharge India number - Vadivel & Sindhu"
          required
        />
      </label>
      <label className={styles.label}>
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
            className={styles.smallBtn}
            onClick={() => setDueDate("")}
          >
            Clear
          </button>
        </div>
      </label>
      <label className={styles.label}>
        Frequency
        <select
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
          className={styles.input}
        >
          {FREQUENCIES.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.label}>
        Importance (P1/P2/P3)
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
      <label className={styles.label}>
        Focus (time horizon)
        <select
          value={timeHorizon}
          onChange={(e) => setTimeHorizon(e.target.value)}
          className={styles.input}
        >
          <option value="">—</option>
          <option value="focus_now">Focus now</option>
          <option value="focus_today">Focus today</option>
          <option value="focus_week">Focus this week</option>
          <option value="focus_month">Focus this month</option>
          <option value="focus_later">Focus later</option>
        </select>
      </label>
      <label className={styles.label}>
        Tags
        <div className={styles.tagRow}>
          {SUGGESTED_TAGS.map((tag) => (
            <button
              key={tag}
              type="button"
              className={`${styles.tagBtn} ${tags.includes(tag) ? styles.tagBtnActive : ""}`}
              onClick={() => toggleTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
        <div className={styles.customTag}>
          <input
            value={customTag}
            onChange={(e) => setCustomTag(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCustomTag())}
            className={styles.input}
            placeholder="Add tag..."
          />
          <button type="button" className={styles.smallBtn} onClick={addCustomTag}>
            Add
          </button>
        </div>
      </label>
      <label className={styles.label}>
        Comments / Next steps
        <textarea
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          className={styles.textarea}
          placeholder="e.g. Reach out to tax consultant, gather documents..."
          rows={3}
        />
      </label>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.actions}>
        <button type="submit" className={styles.btnPrimary} disabled={saving}>
          {saving ? "Saving…" : "Add task"}
        </button>
        <button type="button" className={styles.btnSecondary} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
