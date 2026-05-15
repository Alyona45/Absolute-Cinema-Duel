"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { api } from "@/lib/api";
import { useUserStore } from "@/stores/user-store";
import type { GameSession } from "@/types";

const spring = { type: "spring" as const, stiffness: 180, damping: 22, mass: 0.9 };

const pageOrchestrator = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.05 },
  },
};

const headerReveal = {
  hidden: { opacity: 0, y: -40, filter: "blur(12px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { ...spring, stiffness: 140, damping: 20 },
  },
};

const avatarPop = {
  hidden: { opacity: 0, scale: 0.5, rotate: -8 },
  visible: {
    opacity: 1,
    scale: 1,
    rotate: 0,
    transition: { ...spring, stiffness: 200, damping: 16 },
  },
};

const textSlide = {
  hidden: { opacity: 0, x: -20, filter: "blur(6px)" },
  visible: {
    opacity: 1,
    x: 0,
    filter: "blur(0px)",
    transition: { ...spring },
  },
};

const statPop = (delay: number) => ({
  hidden: { opacity: 0, scale: 0.3, y: 10 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { ...spring, stiffness: 260, damping: 18, delay },
  },
});

const buttonSlide = (delay: number) => ({
  hidden: { opacity: 0, x: 40, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    x: 0,
    filter: "blur(0px)",
    transition: { ...spring, delay },
  },
});

const panelRise = {
  hidden: { opacity: 0, y: 60, filter: "blur(14px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { ...spring, stiffness: 120, damping: 20, delay: 0.3 },
  },
};

const cardReveal = (i: number) => ({
  hidden: { opacity: 0, scale: 0.85, y: 30 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { ...spring, stiffness: 160, damping: 18, delay: 0.45 + i * 0.08 },
  },
});

const editFade = {
  hidden: { opacity: 0, scale: 0.6 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.6 },
  },
};

function ProfileAvatar({ src, name }: { src?: string | null; name: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <motion.div
      variants={avatarPop}
      style={{
        width: 96,
        height: 96,
        position: "relative",
        flexShrink: 0,
        minWidth: 96,
        minHeight: 96,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 7,
          left: 7,
          width: 82,
          height: 82,
          borderRadius: 9999,
          overflow: "hidden",
          background: "#404040",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {src ? (
          <img
            src={src}
            alt={name}
            width={82}
            height={82}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            loading="eager"
            decoding="async"
          />
        ) : (
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 24, userSelect: "none" }}>
            {initials}
          </span>
        )}
      </div>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 96,
          height: 96,
          borderRadius: 9999,
          border: "1.5px solid #E82323",
          pointerEvents: "none",
        }}
      />
    </motion.div>
  );
}

const fullWidth: React.CSSProperties = {
  width: "100vw",
  marginLeft: "calc(-50vw + 50%)",
};
const hPad = "clamp(20px, 7vw, 98px)";

/* Тип элемента истории игр */
interface HistoryItem {
  id: number;
  title: string;
  posterUrl: string | null;
  description: string;
  year: number | null;
}

function HistoryCard({ item, index }: { item: HistoryItem; index: number }) {
  const [flipped, setFlipped] = useState(false);

  return (
    <motion.div
      variants={cardReveal(index)}
      initial="hidden"
      animate="visible"
      whileHover={{ scale: 1.05, y: -6, boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 250, damping: 18 }}
      onClick={() => setFlipped((v) => !v)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setFlipped((v) => !v);
        }
      }}
      aria-label={flipped ? "Показать постер" : "Показать описание"}
      className="profile-history-card"
      style={{
        flexShrink: 0,
        width: 200,
        aspectRatio: "2 / 3",
        height: "auto",
        minHeight: 300,
        borderRadius: 30,
        position: "relative",
        cursor: "pointer",
        perspective: 1200,
      }}
    >
      <motion.div
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        style={{ position: "absolute", inset: 0, transformStyle: "preserve-3d" }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: 30,
            overflow: "hidden",
            background: "#2a2a2e",
            backfaceVisibility: "hidden",
            WebkitBackfaceVisibility: "hidden",
          }}
        >
          {item.posterUrl ? (
            <Image src={item.posterUrl} alt={item.title} fill className="object-cover" sizes="200px" />
          ) : (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "0 12px",
                textAlign: "center",
                fontSize: 12,
                color: "rgba(255,255,255,0.35)",
                lineHeight: "1.4",
              }}
            >
              {item.title || "Без постера"}
            </div>
          )}

          {item.title && (
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                bottom: 0,
                padding: "28px 14px 14px",
                background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.55) 55%, rgba(0,0,0,0) 100%)",
                color: "#fff",
                fontSize: 13,
                fontWeight: 700,
                lineHeight: "16px",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
              }}
            >
              {item.title}{item.year ? ` (${item.year})` : ""}
            </div>
          )}
        </div>

        {/* Обратная сторона — описание фильма */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: 30,
            background: "#F4F4F4",
            color: "#111",
            padding: "18px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
            transform: "rotateY(180deg)",
            backfaceVisibility: "hidden",
            WebkitBackfaceVisibility: "hidden",
          }}
        >
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 800, lineHeight: "18px" }}>
            {item.title}{item.year ? ` (${item.year})` : ""}
          </h3>
          <p
            style={{
              margin: 0,
              fontSize: 12,
              fontWeight: 500,
              lineHeight: "17px",
              color: "#333",
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 12,
              WebkitBoxOrient: "vertical",
            }}
          >
            {item.description || "Описание недоступно."}
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const { userId, username, email, avatarUrl, isGuest, accessToken } = useUserStore();
  const [sessions, setSessions] = useState<GameSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [hydrated, setHydrated] = useState(() =>
    typeof window !== "undefined" ? useUserStore.persist.hasHydrated() : false
  );
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (hydrated) return;
    if (useUserStore.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsub = useUserStore.persist.onFinishHydration(() => setHydrated(true));
    return unsub;
  }, [hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    if (isGuest && !accessToken) {
      router.push("/auth/login");
      return;
    }
    (async () => {
      try {
        setSessions(await api.get<GameSession[]>("/sessions"));
      } catch {
      }
      setLoading(false);
    })();
  }, [hydrated, isGuest, accessToken, router]);

  const finished = sessions.filter((s) => s.status === "FINISHED");
  const wins =
    typeof userId === "number"
      ? finished.filter((s) => s.winner_user_id === userId).length
      : 0;
  const history = finished
    .map((s) => ({
      id: s.id,
      title: s.winner_session_movie?.movie?.title ?? "",
      posterUrl: s.winner_session_movie?.movie?.poster_url ?? null,
      description:
        s.winner_session_movie?.movie?.short_description ||
        s.winner_session_movie?.movie?.description ||
        "",
      year: s.winner_session_movie?.movie?.year ?? null,
    }))
    .filter((i) => i.posterUrl || i.title)
    .slice(0, 10);

  const displayName = username || email || "Пользователь";

  return (
    <motion.div
      variants={pageOrchestrator}
      initial={reducedMotion ? "visible" : "hidden"}
      animate="visible"
      style={{ display: "flex", flexDirection: "column", minHeight: "calc(100dvh - 5.5rem)", gap: 20 }}
    >

      {/* Шапка профиля */}
      <motion.section
        className="profile-header"
        variants={headerReveal}
        style={{
          ...fullWidth,
          background: "rgba(255, 255, 255, 0.07)",
          borderTopLeftRadius: 0,
          borderTopRightRadius: 0,
          borderBottomLeftRadius: 50,
          borderBottomRightRadius: 50,
          paddingTop: 27,
          paddingBottom: 27,
          paddingLeft: hPad,
          paddingRight: hPad,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 20,
          position: "relative",
        }}
      >
        {/* Иконка редактирования — правый верхний угол */}
        <motion.div variants={editFade} style={{ position: "absolute", top: 14, right: 20 }}>
          <Link
            href="/profile/edit"
            aria-label="Редактировать профиль"
            style={{ color: "rgba(255,255,255,0.55)", display: "block" }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M16.4356 3.21193C16.8261 2.8219 17.4592 2.82161 17.8496 3.21193L20.6777 6.04104C21.0681 6.43157 21.0682 7.06462 20.6777 7.4551L7.2422 20.8896H3.00001V16.6475L16.4356 3.21193ZM5.00001 17.4756V18.8896H6.41407L15.7276 9.57619L14.3135 8.16213L5.00001 17.4756ZM4.5293 1.31935C4.70583 0.89355 5.29418 0.893553 5.47071 1.31935L5.72364 1.93068C6.15555 2.97347 6.96155 3.80618 7.97462 4.25685L8.69239 4.57618C9.10267 4.75901 9.10262 5.35621 8.69239 5.53908L7.93263 5.87697C6.94497 6.31625 6.15339 7.11948 5.71387 8.12795L5.4668 8.69339C5.28636 9.10752 4.71366 9.10752 4.53321 8.69339L4.28614 8.12795C3.84661 7.11948 3.05506 6.31625 2.06739 5.87697L1.30762 5.53908C0.897484 5.35622 0.897436 4.75901 1.30762 4.57618L2.0254 4.25685C3.03845 3.80619 3.84446 2.97348 4.27637 1.93068L4.5293 1.31935ZM15.7276 6.74807L17.1426 8.16213L18.5567 6.74807L17.1426 5.334L15.7276 6.74807Z"
                fill="currentColor"
              />
            </svg>
          </Link>
        </motion.div>

        {/* Аватар + имя + статистика */}
        <div className="profile-identity" style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <ProfileAvatar src={avatarUrl} name={displayName} />

          <div
            className="profile-identity-text"
            style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 16 }}
          >
            <motion.div
              variants={textSlide}
              className="profile-name"
              style={{ color: "white", fontSize: 20, fontWeight: 800, lineHeight: "22px", textAlign: "left" }}
            >
              {displayName}
            </motion.div>

            <div className="profile-stats" style={{ display: "flex", alignItems: "flex-start", gap: 40 }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
                <motion.div
                  variants={statPop(0.2)}
                  className="profile-stat-value"
                  style={{ color: "white", fontSize: 32, fontWeight: 500, lineHeight: "22px" }}
                >
                  {wins}
                </motion.div>
                <motion.div
                  variants={textSlide}
                  className="profile-stat-label"
                  style={{ color: "rgba(255,255,255,0.60)", fontSize: 20, fontWeight: 500, lineHeight: "22px" }}
                >
                  побед
                </motion.div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
                <motion.div
                  variants={statPop(0.3)}
                  className="profile-stat-value"
                  style={{ color: "white", fontSize: 32, fontWeight: 500, lineHeight: "22px" }}
                >
                  {sessions.length}
                </motion.div>
                <motion.div
                  variants={textSlide}
                  className="profile-stat-label"
                  style={{ color: "rgba(255,255,255,0.60)", fontSize: 20, fontWeight: 500, lineHeight: "22px" }}
                >
                  игр
                </motion.div>
              </div>
            </div>
          </div>
        </div>

        {/* Кнопки действий */}
        <div className="profile-buttons" style={{ display: "flex", alignItems: "center", gap: 30 }}>
          <motion.button
            variants={buttonSlide(0.25)}
            whileHover={{ scale: 1.04, y: -2, boxShadow: "0px 12px 48px rgba(232, 35, 35, 0.3)" }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            onClick={() => router.push("/create")}
            style={{
              width: 220,
              height: 56,
              background: "#E82323",
              color: "white",
              fontSize: 17,
              fontWeight: 500,
              borderRadius: 1000,
              border: "none",
              cursor: "pointer",
              boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
            }}
          >
            Создать комнату
          </motion.button>
          <motion.button
            variants={buttonSlide(0.35)}
            whileHover={{ scale: 1.04, y: -2, boxShadow: "0px 12px 48px rgba(0, 0, 0, 0.25)" }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            onClick={() => router.push("/join")}
            style={{
              width: 220,
              height: 56,
              background: "white",
              color: "#1A1A1A",
              fontSize: 16,
              fontWeight: 500,
              borderRadius: 1000,
              border: "none",
              cursor: "pointer",
              boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
            }}
          >
            Присоединиться
          </motion.button>
        </div>
      </motion.section>

      {/* Панель истории игр */}
      <motion.section
        className="profile-history"
        variants={panelRise}
        style={{
          ...fullWidth,
          flex: "1 1 0",
          background: "rgba(255, 255, 255, 0.07)",
          borderTopLeftRadius: 50,
          borderTopRightRadius: 50,
          borderBottomLeftRadius: 50,
          borderBottomRightRadius: 50,
          paddingTop: 14,
          paddingBottom: 14,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          style={{ textAlign: "center", color: "white", fontSize: 15, fontWeight: 800, lineHeight: "22px" }}
        >
          История игр
        </motion.div>

        {loading ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              style={{
                width: 28,
                height: 28,
                borderRadius: 9999,
                border: "2px solid rgba(232,35,35,0.25)",
                borderTopColor: "#E82323",
              }}
            />
          </div>
        ) : history.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ ...spring, delay: 0.5 }}
            style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10 }}
          >
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" style={{ color: "rgba(255,255,255,0.15)" }}>
              <rect x="3" y="3" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <path d="M8 21h8M12 17v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span style={{ fontSize: 14, color: "rgba(255,255,255,0.35)" }}>Нет завершённых игр</span>
          </motion.div>
        ) : (
          <div
            style={{
              flex: "1 1 auto",
              minHeight: 320,
              display: "flex",
              alignItems: "center",
              gap: 18,
              overflowX: "auto",
              overflowY: "visible",
              paddingTop: 18,
              paddingBottom: 18,
              paddingLeft: hPad,
              paddingRight: hPad,
              width: "100%",
              scrollbarWidth: "none",
              WebkitOverflowScrolling: "touch",
            }}
          >
            {history.map((item, i) => (
              <HistoryCard key={item.id} item={item} index={i} />
            ))}
          </div>
        )}
      </motion.section>
    </motion.div>
  );
}
