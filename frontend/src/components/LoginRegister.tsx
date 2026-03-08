"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "./AuthContext";
import styles from "./LoginRegister.module.css";

export function LoginRegister() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [emailOrUsername, setEmailOrUsername] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(emailOrUsername.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await register(email.trim(), username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <h1 className={styles.title}>FocusFlow</h1>
        <p className={styles.subtitle}>AI-powered task command center</p>

        <div className={styles.tabs}>
          <button
            type="button"
            className={mode === "login" ? styles.tabActive : styles.tab}
            onClick={() => { setMode("login"); setError(""); }}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === "register" ? styles.tabActive : styles.tab}
            onClick={() => { setMode("register"); setError(""); }}
          >
            Sign up
          </button>
        </div>

        {error && <p className={styles.error}>{error}</p>}

        {mode === "login" && (
          <form onSubmit={handleLogin} className={styles.form}>
            <label className={styles.label}>Email or username</label>
            <input
              type="text"
              className={styles.input}
              value={emailOrUsername}
              onChange={(e) => setEmailOrUsername(e.target.value)}
              placeholder="you@example.com or myname"
              required
              autoComplete="username"
            />
            <label className={styles.label}>Password</label>
            <input
              type="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <button type="submit" className={styles.submit} disabled={loading}>
              {loading ? "Signing in…" : "Log in"}
            </button>
            <Link href="/forgot-password" className={styles.forgotLink}>Forgot password?</Link>
          </form>
        )}

        {mode === "register" && (
          <form onSubmit={handleRegister} className={styles.form}>
            <label className={styles.label}>Email</label>
            <input
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
            <label className={styles.label}>Username</label>
            <input
              type="text"
              className={styles.input}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="myname"
              required
              autoComplete="username"
            />
            <label className={styles.label}>Password (min 8 characters)</label>
            <input
              type="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
            <button type="submit" className={styles.submit} disabled={loading}>
              {loading ? "Creating account…" : "Sign up"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
