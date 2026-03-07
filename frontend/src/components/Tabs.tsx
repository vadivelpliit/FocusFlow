"use client";

import styles from "./Tabs.module.css";

export type TabId = "tasks" | "chat" | "schedule";

interface TabsProps {
  active: TabId;
  onSelect: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "tasks", label: "Tasks", icon: "☰" },
  { id: "chat", label: "AI Chat", icon: "🤖" },
  { id: "schedule", label: "Week Planner", icon: "📅" },
];

export function Tabs({ active, onSelect }: TabsProps) {
  return (
    <nav className={styles.tabs}>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`${styles.tab} ${active === tab.id ? styles.active : ""}`}
          onClick={() => onSelect(tab.id)}
        >
          <span className={styles.icon}>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
