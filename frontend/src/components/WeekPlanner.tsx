"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import styles from "./WeekPlanner.module.css";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DESIRED_ACTIVITIES = [
  "office",
  "admin",
  "cook",
  "daughter",
  "kitchen",
  "projects",
  "study AI",
  "exercise",
  "expense tracker",
  "clean",
  "library",
  "Costco",
];

interface ScheduleBlock {
  id?: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  label: string;
  notes?: string | null;
}

export function WeekPlanner() {
  const [selectedDay, setSelectedDay] = useState(0);
  const [inputs, setInputs] = useState<string[]>(Array(7).fill(""));
  const [desiredActivities, setDesiredActivities] = useState<string[]>([]);
  const [blocks, setBlocks] = useState<ScheduleBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [proposing, setProposing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInputs = useCallback(async () => {
    try {
      const data = await api.getScheduleInputs();
      setInputs(data.map((d) => d.user_description || ""));
    } catch {
      setInputs(Array(7).fill(""));
    }
  }, []);

  const loadBlocks = useCallback(async () => {
    try {
      const data = await api.getScheduleBlocks();
      setBlocks(data);
    } catch {
      setBlocks([]);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadInputs(), loadBlocks()]).finally(() => setLoading(false));
  }, [loadInputs, loadBlocks]);

  const saveInputs = async () => {
    setError(null);
    try {
      await api.putScheduleInputs(
        inputs.map((user_description, day_of_week) => ({ day_of_week, user_description: user_description || null }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const toggleActivity = (a: string) => {
    setDesiredActivities((prev) => (prev.includes(a) ? prev.filter((x) => x !== a) : [...prev, a]));
  };

  const handlePropose = async () => {
    setError(null);
    setProposing(true);
    try {
      await saveInputs();
      const { blocks: proposed } = await api.proposeSchedule(desiredActivities);
      setBlocks(proposed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate plan");
    } finally {
      setProposing(false);
    }
  };

  const handleApply = async () => {
    setError(null);
    try {
      await api.applySchedule(blocks.map((b) => ({ day_of_week: b.day_of_week, start_time: b.start_time, end_time: b.end_time, label: b.label })));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save schedule");
    }
  };

  const blocksByDay = blocks.reduce<Record<number, ScheduleBlock[]>>((acc, b) => {
    if (!acc[b.day_of_week]) acc[b.day_of_week] = [];
    acc[b.day_of_week].push(b);
    return acc;
  }, {});

  if (loading) return <div className={styles.loading}>Loading…</div>;

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <h1 className={styles.title}>Week Planner</h1>
        <p className={styles.tagline}>AI-scheduled · progress tracked · adaptive</p>
        <button type="button" className={styles.planBtn} onClick={handlePropose} disabled={proposing}>
          {proposing ? "Generating…" : "Plan My Week with AI"}
        </button>
      </header>

      <div className={styles.dayTabs}>
        {DAY_NAMES.map((name, i) => (
          <button
            key={i}
            type="button"
            className={`${styles.dayTab} ${selectedDay === i ? styles.dayTabActive : ""}`}
            onClick={() => setSelectedDay(i)}
          >
            {name}
          </button>
        ))}
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Describe your current week</h2>
        <p className={styles.hint}>What you do on each day (free-form). Used to generate a realistic schedule.</p>
        <div className={styles.inputGrid}>
          {DAY_NAMES.map((name, i) => (
            <label key={i} className={styles.inputLabel}>
              {name}
              <textarea
                value={inputs[i]}
                onChange={(e) => setInputs((prev) => { const n = [...prev]; n[i] = e.target.value; return n; })}
                onBlur={saveInputs}
                placeholder={`What I do on ${name}...`}
                className={styles.textarea}
                rows={2}
              />
            </label>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Desired activities</h2>
        <p className={styles.hint}>Select what you want to fit into your week.</p>
        <div className={styles.activities}>
          {DESIRED_ACTIVITIES.map((a) => (
            <button
              key={a}
              type="button"
              className={`${styles.activityBtn} ${desiredActivities.includes(a) ? styles.activityBtnActive : ""}`}
              onClick={() => toggleActivity(a)}
            >
              {a}
            </button>
          ))}
        </div>
      </section>

      {error && <p className={styles.error}>{error}</p>}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Your week</h2>
        <div className={styles.blocksGrid}>
          {DAY_NAMES.map((_, dayIndex) => (
            <div key={dayIndex} className={styles.dayColumn}>
              <h3 className={styles.dayName}>{DAY_NAMES[dayIndex]}</h3>
              {(blocksByDay[dayIndex] || [])
                .sort((a, b) => a.start_time.localeCompare(b.start_time))
                .map((b, i) => (
                  <div key={i} className={styles.block}>
                    <span className={styles.blockTime}>{b.start_time} – {b.end_time}</span>
                    <span className={styles.blockLabel}>{b.label}</span>
                  </div>
                ))}
              {(!blocksByDay[dayIndex] || blocksByDay[dayIndex].length === 0) && (
                <p className={styles.emptyDay}>No blocks</p>
              )}
            </div>
          ))}
        </div>
        {blocks.length > 0 && (
          <button type="button" className={styles.applyBtn} onClick={handleApply}>
            Save schedule
          </button>
        )}
      </section>
    </div>
  );
}
