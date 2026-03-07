const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Task {
  id: number;
  detail: string;
  due_date: string | null;
  frequency: string;
  comments: string | null;
  importance: string | null;
  time_horizon: string | null;
  tags: string[] | null;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  detail: string;
  due_date?: string | null;
  frequency?: string;
  comments?: string | null;
  importance?: string | null;
  time_horizon?: string | null;
  tags?: string[] | null;
}

export interface TaskUpdate {
  detail?: string;
  due_date?: string | null;
  frequency?: string;
  comments?: string | null;
  importance?: string | null;
  time_horizon?: string | null;
  tags?: string[] | null;
  completed?: boolean;
}

export interface TaskCounts {
  total: number;
  completed: number;
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit & { params?: Record<string, string> }
): Promise<T> {
  const { params, ...init } = options || {};
  const url = new URL(path, API_BASE);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v != null && v !== "") url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getTasks: (params?: {
    completed?: boolean;
    importance?: string;
    time_horizon?: string;
    tag?: string;
    search?: string;
  }) => {
    const p: Record<string, string> = {};
    if (params) {
      if (params.completed !== undefined) p.completed = String(params.completed);
      if (params.importance) p.importance = params.importance;
      if (params.time_horizon) p.time_horizon = params.time_horizon;
      if (params.tag) p.tag = params.tag;
      if (params.search) p.search = params.search;
    }
    return fetchApi<Task[]>("/tasks", { params: p });
  },

  getTask: (id: number) => fetchApi<Task>(`/tasks/${id}`),

  getCounts: () => fetchApi<TaskCounts>("/tasks/counts"),

  createTask: (task: TaskCreate) =>
    fetchApi<Task>("/tasks", {
      method: "POST",
      body: JSON.stringify(task),
    }),

  updateTask: (id: number, task: TaskUpdate) =>
    fetchApi<Task>(`/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(task),
    }),

  deleteTask: (id: number) =>
    fetchApi<void>(`/tasks/${id}`, { method: "DELETE" }),

  /** Run LLM to assign time_horizon and importance to all incomplete tasks. */
  prioritize: () =>
    fetchApi<{ updated: number }>("/tasks/prioritize", { method: "POST" }),

  /** Send a message to AI chat; returns suggestions based on tasks. */
  chat: (message: string) =>
    fetchApi<{ reply: string }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  // Schedule (Week Planner)
  getScheduleInputs: () => fetchApi<{ day_of_week: number; user_description: string | null }[]>("/schedule/inputs"),
  putScheduleInputs: (inputs: { day_of_week: number; user_description: string | null }[]) =>
    fetchApi<{ ok: boolean }>("/schedule/inputs", { method: "PUT", body: JSON.stringify({ inputs }) }),
  getScheduleBlocks: () =>
    fetchApi<{ id: number; day_of_week: number; start_time: string; end_time: string; label: string; notes: string | null }[]>(
      "/schedule/blocks"
    ),
  proposeSchedule: (desired_activities: string[]) =>
    fetchApi<{ blocks: { day_of_week: number; start_time: string; end_time: string; label: string }[] }>(
      "/schedule/propose",
      { method: "POST", body: JSON.stringify({ desired_activities }) }
    ),
  applySchedule: (blocks: { day_of_week: number; start_time: string; end_time: string; label: string }[]) =>
    fetchApi<unknown>("/schedule/apply", { method: "POST", body: JSON.stringify({ blocks }) }),
};
