"use client";

import styles from "./PlaceholderPanel.module.css";

interface PlaceholderPanelProps {
  title: string;
  message: string;
}

export function PlaceholderPanel({ title, message }: PlaceholderPanelProps) {
  return (
    <div className={styles.wrapper}>
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.message}>{message}</p>
    </div>
  );
}
