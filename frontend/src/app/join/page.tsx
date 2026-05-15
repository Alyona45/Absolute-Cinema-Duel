"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast-store";
import { useUserStore } from "@/stores/user-store";

export default function JoinPage() {
  const router = useRouter();
  const { setGuest, setRuntimeUserId } = useUserStore();
  const { addToast } = useToastStore();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  const handleJoin = async () => {
    if (!code.trim()) return;
    setLoading(true);
    const inviteCode = code.trim().toUpperCase();
    try {
      const result = await api.post<{ user_id: string; username: string }>(
        `/rooms/${inviteCode}/join`,
      );
      setRuntimeUserId(result.user_id);
      if (result.user_id.startsWith("guest:")) {
        setGuest(result.username, result.user_id);
      }
      router.push(`/session/${inviteCode}`);
    } catch (err) {
      console.error("[JOIN] Error:", err);
      addToast("Комната не найдена", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "calc(100dvh - 5.5rem)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px clamp(20px, 8vw, 388px)",
        gap: 48,
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 220, damping: 22 }}
        style={{
          width: "min(100%, 650px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 30,
        }}
      >
        <h1
          style={{
            color: "#fff",
            fontSize: 19,
            fontWeight: 800,
            textAlign: "center",
            margin: 0,
          }}
        >
          Введите код комнаты:
        </h1>

        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && handleJoin()}
          placeholder="12345"
          autoFocus
          style={{
            width: "min(100%, 400px)",
            padding: "15px",
            background: "rgba(255,255,255,0.07)",
            borderRadius: 16,
            border: "none",
            outline: "none",
            color: "#fff",
            fontSize: 19,
            fontWeight: 510,
            textAlign: "center",
            letterSpacing: "0.18em",
            fontFamily: "'SF Pro', 'Inter', sans-serif",
          }}
          className="placeholder:text-[#B8B8B8]"
        />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, type: "spring", stiffness: 220, damping: 22 }}
        style={{ width: "min(100%, 330px)" }}
      >
        <motion.button
          type="button"
          onClick={handleJoin}
          disabled={loading || !code.trim()}
          whileHover={{
            scale: 1.02,
            boxShadow: "0px 12px 48px rgba(232,35,35,0.35)",
          }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          style={{
            width: "100%",
            height: 60,
            background: "#E82323",
            color: "#fff",
            fontSize: 19,
            fontWeight: 860,
            fontFamily: "'SF Pro', 'Inter', sans-serif",
            borderRadius: 16,
            border: "none",
            cursor: loading || !code.trim() ? "not-allowed" : "pointer",
            boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
            opacity: loading || !code.trim() ? 0.6 : 1,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
          }}
        >
          {loading ? (
            <span
              style={{
                width: 16,
                height: 16,
                borderRadius: "50%",
                border: "2px solid rgba(255,255,255,0.4)",
                borderTopColor: "#fff",
                animation: "spin 0.7s linear infinite",
              }}
            />
          ) : null}
          Присоединиться
        </motion.button>
      </motion.div>
    </div>
  );
}
