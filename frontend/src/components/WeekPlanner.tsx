"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import styles from "./WeekPlanner.module.css";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function formatDateKey(d: Date): string {
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

function getMonthGrid(year: number, month: number): (number | null)[][] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startDay = first.getDay();
  const daysInMonth = last.getDate();
  const rows: (number | null)[][] = [];
  let row: (number | null)[] = [];
  for (let i = 0; i < startDay; i++) row.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    row.push(d);
    if (row.length === 7) {
      rows.push(row);
      row = [];
    }
  }
  if (row.length) {
    while (row.length < 7) row.push(null);
    rows.push(row);
  }
  return rows;
}

export function WeekPlanner() {
  const [today] = useState(() => formatDateKey(new Date()));
  const [currentMonth, setCurrentMonth] = useState(() => new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(() => new Date().getFullYear());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [whatIDid, setWhatIDid] = useState("");
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [recommendWindow, setRecommendWindow] = useState<{ start: string; end: string } | null>(null);
  const [loadingLog, setLoadingLog] = useState(false);
  const [savingLog, setSavingLog] = useState(false);
  const [loadingRecommend, setLoadingRecommend] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDayLog = useCallback(async (dateStr: string) => {
    setLoadingLog(true);
    setError(null);
    try {
      const res = await api.getDayLog(dateStr);
      setWhatIDid(res.content || "");
    } catch (e) {
      setWhatIDid("");
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoadingLog(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDate) loadDayLog(selectedDate);
    else setWhatIDid("");
  }, [selectedDate, loadDayLog]);

  const saveDayLog = async () => {
    if (!selectedDate) return;
    setSavingLog(true);
    setError(null);
    try {
      await api.putDayLog(selectedDate, whatIDid.trim() || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSavingLog(false);
    }
  };

  const fetchRecommend = async () => {
    const dateStr = selectedDate || today;
    setLoadingRecommend(true);
    setError(null);
    setRecommendation(null);
    try {
      const res = await api.getRecommend(dateStr);
      setRecommendation(res.recommendation);
      setRecommendWindow({ start: res.window_start, end: res.window_end });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to get recommendation");
    } finally {
      setLoadingRecommend(false);
    }
  };

  const grid = getMonthGrid(currentYear, currentMonth);
  const monthLabel = new Date(currentYear, currentMonth, 1).toLocaleString("default", { month: "long", year: "numeric" });

  const handleSelectDay = (day: number) => {
    const dateStr = formatDateKey(new Date(currentYear, currentMonth, day));
    setSelectedDate(dateStr);
  };

  const prevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((y) => y - 1);
    } else setCurrentMonth((m) => m - 1);
  };

  const nextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((y) => y + 1);
    } else setCurrentMonth((m) => m + 1);
  };

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <h1 className={styles.title}>Week Planner</h1>
        <p className={styles.tagline}>Click a date and enter what you did. Below, get an AI recommendation for rest of week and next week.</p>
      </header>

      <section className={styles.calendarSection}>
        <div className={styles.monthNav}>
          <button type="button" className={styles.navBtn} onClick={prevMonth}>←</button>
          <span className={styles.monthLabel}>{monthLabel}</span>
          <button type="button" className={styles.navBtn} onClick={nextMonth}>→</button>
        </div>
        <table className={styles.calendar}>
          <thead>
            <tr>
              {DAY_NAMES.map((d) => (
                <th key={d} className={styles.calHead}>{d}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.map((row, ri) => (
              <tr key={ri}>
                {row.map((day, di) => (
                  <td key={di} className={styles.calCell}>
                    {day != null ? (
                      <button
                        type="button"
                        className={`${styles.dayBtn} ${
                          selectedDate === formatDateKey(new Date(currentYear, currentMonth, day)) ? styles.dayBtnSelected : ""
                        } ${today === formatDateKey(new Date(currentYear, currentMonth, day)) ? styles.dayBtnToday : ""}`}
                        onClick={() => handleSelectDay(day)}
                      >
                        {day}
                      </button>
                    ) : null}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {selectedDate && (
          <div className={styles.whatIDidBlock}>
            <h3 className={styles.sectionLabel}>{selectedDate} – What I did</h3>
            <p className={styles.hint}>Free-form note for this day. Saved when you blur or click Save. AI uses past entries to learn your patterns.</p>
            {loadingLog ? (
              <p className={styles.muted}>Loading…</p>
            ) : (
              <>
                <textarea
                  value={whatIDid}
                  onChange={(e) => setWhatIDid(e.target.value)}
                  onBlur={saveDayLog}
                  placeholder="e.g. Morning: exercise, breakfast. 9-5 office. Evening: cooked, time with daughter."
                  className={styles.textarea}
                  rows={4}
                />
                <button type="button" className={styles.saveBtn} onClick={saveDayLog} disabled={savingLog}>
                  {savingLog ? "Saving…" : "Save"}
                </button>
              </>
            )}
          </div>
        )}

        {!selectedDate && (
          <p className={styles.pickHint}>Click a date to enter what you did that day.</p>
        )}
      </section>

      <section className={styles.recommendSection}>
        <h2 className={styles.recommendTitle}>AI recommendation</h2>
        <p className={styles.hint}>Plan for rest of this week and next full week. Click the button to refresh.</p>
        <button type="button" className={styles.recommendBtn} onClick={fetchRecommend} disabled={loadingRecommend}>
          {loadingRecommend ? "Thinking…" : "Get recommendation"}
        </button>
        {recommendWindow && (
          <p className={styles.windowLabel}>Plan for {recommendWindow.start} through {recommendWindow.end}</p>
        )}
        {recommendation && (
          <div className={styles.recommendationBox}>
            <pre className={styles.recommendationText}>{recommendation}</pre>
          </div>
        )}
        {error && <p className={styles.error}>{error}</p>}
      </section>
    </div>
  );
}
