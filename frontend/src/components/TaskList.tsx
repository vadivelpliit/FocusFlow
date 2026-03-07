"use client";

import { useCallback, useEffect, useState } from "react";
import type { Task } from "@/lib/api";
import { api } from "@/lib/api";
import { getSectionForHorizon, TIME_HORIZON_SECTIONS } from "@/lib/utils";
import { TaskRow } from "./TaskRow";
import { AddTaskForm } from "./AddTaskForm";
import { AIInsightsCard } from "./AIInsightsCard";
import styles from "./TaskList.module.css";

type Filter = "all" | "P1" | "P2" | "P3" | string;

interface TaskListProps {
  onTasksChange?: () => void;
  onChatClick?: () => void;
}

export function TaskList({ onTasksChange, onChatClick }: TaskListProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [counts, setCounts] = useState({ total: 0, completed: 0 });
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [showCompleted, setShowCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  const loadTasks = useCallback(async () => {
    try {
      setError(null);
      const params: { completed?: boolean; importance?: string; tag?: string; search?: string } = {};
      if (filter !== "all") {
        if (["P1", "P2", "P3"].includes(filter)) params.importance = filter;
        else params.tag = filter;
      }
      if (search) params.search = search;
      params.completed = showCompleted;
      const [taskList, countData] = await Promise.all([
        api.getTasks(params),
        api.getCounts(),
      ]);
      setTasks(taskList);
      setCounts(countData);
      onTasksChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [filter, search, showCompleted]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleToggleComplete = async (id: number, completed: boolean) => {
    try {
      await api.updateTask(id, { completed });
      loadTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  };

  const handleUpdate = async (id: number, updates: Partial<Task>) => {
    try {
      await api.updateTask(id, updates);
      loadTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteTask(id);
      loadTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleCreated = () => {
    setShowAddForm(false);
    loadTasks();
  };

  const handlePrioritize = async () => {
    await api.prioritize();
    loadTasks();
  };

  const activeTasks = tasks.filter((t) => !t.completed);
  const completedTasks = tasks.filter((t) => t.completed);
  const bySection = TIME_HORIZON_SECTIONS.map((section) => ({
    ...section,
    tasks: activeTasks.filter((t) => getSectionForHorizon(t.time_horizon) === section.id),
  }));

  const filterPills: { id: Filter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "P1", label: "P1" },
    { id: "P2", label: "P2" },
    { id: "P3", label: "P3" },
    { id: "financial", label: "financial" },
    { id: "call", label: "call" },
  ];

  if (loading) return <div className={styles.loading}>Loading tasks…</div>;
  if (error) return <div className={styles.error}>{error}</div>;

  return (
    <div className={styles.wrapper}>
      <AIInsightsCard onPrioritize={handlePrioritize} onChatClick={onChatClick} />
      <div className={styles.toolbar}>
        <input
          type="search"
          placeholder="Search tasks..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={styles.search}
        />
        <div className={styles.filters}>
          {filterPills.map((pill) => (
            <button
              key={pill.id}
              type="button"
              className={`${styles.pill} ${filter === pill.id ? styles.pillActive : ""}`}
              onClick={() => setFilter(pill.id)}
            >
              {pill.label}
            </button>
          ))}
          <button
            type="button"
            className={`${styles.pill} ${showCompleted ? styles.pillActive : ""}`}
            onClick={() => setShowCompleted(!showCompleted)}
          >
            done
          </button>
        </div>
      </div>

      {showAddForm ? (
        <AddTaskForm onCreated={handleCreated} onCancel={() => setShowAddForm(false)} />
      ) : (
        <button type="button" className={styles.addBtn} onClick={() => setShowAddForm(true)}>
          + Add task
        </button>
      )}

      <div className={styles.sections}>
        {showCompleted ? (
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>
              <span className={styles.sectionIcon_someday}>•</span>
              Completed
              <span className={styles.remaining}>{completedTasks.length}</span>
            </h2>
            {completedTasks.length === 0 ? (
              <p className={styles.empty}>No completed tasks</p>
            ) : (
              completedTasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  onToggleComplete={handleToggleComplete}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                />
              ))
            )}
          </div>
        ) : (
          bySection.map((section) => (
            <div key={section.id} className={styles.section}>
              <h2 className={styles.sectionTitle}>
                <span className={styles[`sectionIcon_${section.id}`]}>•</span>
                {section.label}
                <span className={styles.remaining}>{section.tasks.length} remaining</span>
              </h2>
              {section.tasks.length === 0 ? (
                <p className={styles.empty}>No tasks</p>
              ) : (
                section.tasks.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    onToggleComplete={handleToggleComplete}
                    onUpdate={handleUpdate}
                    onDelete={handleDelete}
                  />
                ))
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
