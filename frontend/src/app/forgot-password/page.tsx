"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import styles from "./forgot-password.module.css";


export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [resetLink, setResetLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    setResetLink(null);
    setLoading(true);
    try {
      const res = await api.auth.forgotPassword(email.trim());
      setMessage(res.message);
      if (res.reset_link) setResetLink(res.reset_link);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <h1 className={styles.title}>Reset password</h1>
        <p className={styles.subtitle}>Enter your email and we’ll send you a link to reset your password.</p>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.label}>Email</label>
          <input
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <button type="submit" className={styles.submit} disabled={loading}>
            {loading ? "Sending…" : "Send reset link"}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {resetLink && (
          <p className={styles.linkBox}>
            <a href={resetLink} className={styles.link}>Use this link to reset (dev)</a>
          </p>
        )}
        <Link href="/" className={styles.back}>Back to login</Link>
      </div>
    </div>
  );
}
