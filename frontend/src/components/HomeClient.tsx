"use client";

import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { Header } from "./Header";
import { Tabs, type TabId } from "./Tabs";
import { TaskList } from "./TaskList";
import { AIChat } from "./AIChat";
import { WeekPlanner } from "./WeekPlanner";
import { api } from "@/lib/api";
import styles from "./HomeClient.module.css";

export function HomeClient() {
  const { user, logout } = useAuth();
  const [tab, setTab] = useState<TabId>("tasks");
  const [counts, setCounts] = useState({ total: 0, completed: 0 });

  const refreshCounts = () => {
    api.getCounts().then(setCounts).catch(() => {});
  };

  useEffect(() => {
    refreshCounts();
  }, [tab]);

  return (
    <main className={styles.main}>
      <Header
        completed={counts.completed}
        total={counts.total}
        username={user?.username}
        onLogout={logout}
      />
      <Tabs active={tab} onSelect={setTab} />
      <div className={styles.panel}>
        {tab === "tasks" && (
          <TaskList
            onTasksChange={refreshCounts}
            onChatClick={() => setTab("chat")}
          />
        )}
        {tab === "chat" && <AIChat />}
        {tab === "schedule" && <WeekPlanner />}
      </div>
    </main>
  );
}
