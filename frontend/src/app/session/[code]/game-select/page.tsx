"use client";

import { useEffect, useState, useRef } from "react";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useGameStore } from "@/stores/game-store";
import { useSessionStore } from "@/stores/session-store";
import { useUserStore } from "@/stores/user-store";
import { api } from "@/lib/api";
import { getWsBaseUrl } from "@/lib/constants";
import type { SessionParticipant } from "@/types";

const games = [
  {
    id: "flappy" as const,
    name: "Flappy Films",
    poster: "/assets/games/flappy.png",
    fallbackIcon: "🐦",
    fallbackBg: "#E82323",
  },
  {
    id: "movieco" as const,
    name: "MovieCO",
    poster: "/assets/games/movieco.png",
    fallbackIcon: "🎬",
    fallbackBg: "#8B5CF6",
  },
];

function GameCard({
  game,
  selected,
  onSelect,
  index,
}: {
  game: (typeof games)[number];
  selected: boolean;
  onSelect: () => void;
  index: number;
}) {
  return (
    <motion.button
      type="button"
      onClick={onSelect}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 + index * 0.08, type: "spring", stiffness: 220, damping: 22 }}
      whileHover={{ y: -4, scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      style={{
        width: 160,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 20,
        background: "transparent",
        border: "none",
        padding: 0,
        cursor: "pointer",
      }}
    >
      <div
        style={{
          position: "relative",
          width: 160,
          height: 160,
          borderRadius: 10,
          overflow: "hidden",
          outline: selected ? "2px solid #E82323" : "none",
          outlineOffset: selected ? 2 : 0,
          background: game.fallbackBg + "25",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
          transition: "outline 160ms ease",
        }}
      >
        <span
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 56,
            pointerEvents: "none",
            zIndex: 0,
          }}
        >
          {game.fallbackIcon}
        </span>
        <Image
          src={game.poster}
          alt={game.name}
          fill
          sizes="160px"
          className="object-cover"
          unoptimized
          style={{ zIndex: 1 }}
        />
      </div>

      <span
        style={{
          color: "#fff",
          fontSize: 16,
          fontWeight: 700,
          lineHeight: "20px",
        }}
      >
        {game.name}
      </span>
    </motion.button>
  );
}

export default function GameSelectPage() {
  const params = useParams();
  const router = useRouter();
  const code = params.code as string;
  const { gameType, setGameType } = useGameStore();
  const { participants: cachedParticipants, session } = useSessionStore();
  const { runtimeUserId } = useUserStore();

  const [participants, setParticipants] = useState<SessionParticipant[]>(
    cachedParticipants,
  );

  useEffect(() => {
    if (cachedParticipants.length > 0) {
      setParticipants(cachedParticipants);
      return;
    }
    if (!session?.id) return;
    let cancelled = false;
    (async () => {
      try {
        const list = await api.get<SessionParticipant[]>(
          `/sessions/${session.id}/participants`,
        );
        if (!cancelled) setParticipants(list);
      } catch {
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cachedParticipants, session?.id]);

  const isHost = participants.some((p) => {
    const runtimeId =
      p.user_id != null ? String(p.user_id) : `guest:${p.guest_id}`;
    return p.is_host && runtimeId === runtimeUserId;
  });

  const navigateToGame = (type: "flappy" | "movieco") => {
    setGameType(type);
    if (type === "flappy") {
      router.push(`/session/${code}/flappy`);
    } else {
      router.push(`/session/${code}/movies?next=movieco`);
    }
  };

  const { accessToken } = useUserStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runtimeUserId) return;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      const wsBase = getWsBaseUrl();
      const url = `${wsBase}/ws/${code}/${runtimeUserId}${accessToken ? `?token=${accessToken}` : ""}`;
      const socket = new WebSocket(url);
      wsRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "GAME_SELECTED") {
            const t = msg.payload?.game_type;
            if (t === "flappy" || t === "movieco") {
              navigateToGame(t);
            }
          } else if (msg.type === "ROOM_STATE") {
            const t = msg.payload?.selected_game;
            if (t === "flappy" || t === "movieco") {
              navigateToGame(t);
            }
          }
        } catch {
        }
      };

      socket.onclose = (event) => {
        if (cancelled) return;
        if (event.code === 4001) return;
        reconnectTimer = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, [runtimeUserId, accessToken, code]);

  const handleSelect = async (type: "flappy" | "movieco") => {
    if (!isHost) return;
    try {
      await api.post(`/rooms/${code}/select-game`, { game_type: type });
    } catch {
    }
    navigateToGame(type);
  };

  return (
    <div
      style={{
        minHeight: "calc(100dvh - 5.5rem)",
        display: "flex",
        flexDirection: "column",
        padding: "32px clamp(20px, 6vw, 80px) 40px",
        gap: 32,
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 220, damping: 22 }}
        style={{ display: "flex", flexDirection: "column", gap: 12 }}
      >
        <h1
          style={{
            color: "white",
            fontSize: 32,
            fontWeight: 700,
            lineHeight: 1.1,
            margin: 0,
          }}
        >
          {isHost ? "Выбор игры" : "Ожидание хоста"}
        </h1>
        <p
          style={{
            color: "#A0A0A0",
            fontSize: 15,
            fontWeight: 700,
            margin: 0,
          }}
        >
          {isHost
            ? "Each player uses their own phone"
            : "Хост комнаты сейчас выбирает игру"}
        </p>
      </motion.div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 23,
          rowGap: 40,
          alignContent: "flex-start",
          justifyContent: "center",
          pointerEvents: isHost ? "auto" : "none",
          opacity: isHost ? 1 : 0.55,
          filter: isHost ? "none" : "grayscale(0.35)",
          transition: "opacity 200ms ease, filter 200ms ease",
        }}
      >
        {games.map((game, i) => (
          <GameCard
            key={game.id}
            game={game}
            index={i}
            selected={gameType === game.id}
            onSelect={() => handleSelect(game.id)}
          />
        ))}
      </div>
    </div>
  );
}
