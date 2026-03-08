"use client";

import styles from "./Header.module.css";

interface HeaderProps {
  completed: number;
  total: number;
  username?: string;
  onLogout?: () => void;
}

export function Header({ completed, total, username, onLogout }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <h1 className={styles.title}>FocusFlow</h1>
        <p className={styles.tagline}>AI-powered task command center</p>
      </div>
      <div className={styles.right}>
        {username != null && (
          <span className={styles.username}>{username}</span>
        )}
        {onLogout != null && (
          <button type="button" className={styles.logout} onClick={onLogout}>
            Log out
          </button>
        )}
        <div className={styles.stats}>
          <span className={styles.completedLabel}>COMPLETED</span>
          <span className={styles.count}>
            {completed}/{total}
          </span>
        </div>
      </div>
    </header>
  );
}
