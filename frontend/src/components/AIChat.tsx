"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import styles from "./AIChat.module.css";

const SUGGESTED_PROMPTS = [
  "What should I do today?",
  "I have 30 minutes – what should I do?",
  "Batch my tasks",
  "What's at risk?",
  "Plan my week",
];

const INITIAL_GREETING =
  "Hi! I've looked at your tasks. You can ask me what to do today, what to do with a short block of time, what's at risk, or how to batch similar tasks. What would you like help with?";

type Message = { role: "user" | "assistant"; content: string };

export function AIChat() {
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", content: INITIAL_GREETING }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string) => {
    const msg = text.trim();
    if (!msg || loading) return;
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);
    try {
      const { reply } = await api.chat(msg);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to get reply");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.messages}>
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? styles.userBubble : styles.assistantBubble}>
            <div className={styles.bubbleContent}>{m.content}</div>
          </div>
        ))}
        {loading && (
          <div className={styles.assistantBubble}>
            <div className={styles.bubbleContent}>Thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.suggested}>
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className={styles.suggestedBtn}
            onClick={() => sendMessage(prompt)}
            disabled={loading}
          >
            {prompt}
          </button>
        ))}
      </div>
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything about your tasks..."
          className={styles.input}
          disabled={loading}
        />
        <button type="submit" className={styles.sendBtn} disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
