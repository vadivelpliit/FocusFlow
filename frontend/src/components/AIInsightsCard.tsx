"use client";

import { useState } from "react";
import styles from "./AIInsightsCard.module.css";

interface AIInsightsCardProps {
  onPrioritize: () => Promise<void>;
  onChatClick?: () => void;
}

export function AIInsightsCard({ onPrioritize, onChatClick }: AIInsightsCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handlePrioritize = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await onPrioritize();
      setMessage("Priorities updated. Tasks are now in Urgent / Important / Someday with P1–P3.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Prioritization failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.card}>
      <button
        type="button"
        className={styles.header}
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
      >
        <span className={styles.title}>
          <span className={styles.icon}>⚡</span> AI INSIGHTS
        </span>
        <span className={styles.chevron}>{collapsed ? "▶" : "▼"}</span>
      </button>
      {!collapsed && (
        <div className={styles.body}>
          <p className={styles.description}>
            Let AI assign priorities based on due dates, financial impact, and effort. Tasks will be placed in Urgent, Important, or Someday and given P1–P3.
          </p>
          {message && (
            <p className={message.startsWith("Priorities") ? styles.success : styles.error}>
              {message}
            </p>
          )}
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={handlePrioritize}
              disabled={loading}
            >
              {loading ? "Prioritizing…" : "Prioritize my tasks"}
            </button>
            {onChatClick && (
              <button type="button" className={styles.btnSecondary} onClick={onChatClick}>
                Chat with AI for more →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
