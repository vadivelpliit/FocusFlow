"use client";

import { useAuth } from "@/components/AuthContext";
import { HomeClient } from "@/components/HomeClient";
import { LoginRegister } from "@/components/LoginRegister";

export default function Home() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--gray-500)" }}>
        Loading…
      </div>
    );
  }

  if (!user) {
    return <LoginRegister />;
  }

  return <HomeClient />;
}
