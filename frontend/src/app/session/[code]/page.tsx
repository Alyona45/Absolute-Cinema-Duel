"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session-store";
import { useToastStore } from "@/stores/toast-store";
import { useUserStore } from "@/stores/user-store";
import { getWsBaseUrl } from "@/lib/constants";
import { copyToClipboard } from "@/lib/utils";
import type {
  GameSession,
  SessionParticipant,
  SessionMovie,
  RoomState,
} from "@/types";

export default function LobbyPage() {
  const params = useParams();
  const router = useRouter();
  const code = params.code as string;
  const { addToast } = useToastStore();
  const { accessToken, userId, runtimeUserId, guestName, setRuntimeUserId, setGuest } = useUserStore();
  const { session, setSession, participants, setParticipants, movies, setMovies } =
    useSessionStore();
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [wsReady, setWsReady] = useState(false);

  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    if (useUserStore.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsub = useUserStore.persist.onFinishHydration(() => setHydrated(true));
    return unsub;
  }, []);

  const autoJoinAttempted = useRef(false);
  const fetchSessionRef = useRef<(() => Promise<void>) | undefined>(undefined);

  const fetchSession = useCallback(async () => {
    try {
      const found = await api.get<GameSession>(`/sessions/by-code/${code}`);
      setSession(found);

      const [partsInit, moviesInit] = await Promise.all([
        api.get<SessionParticipant[]>(`/sessions/${found.id}/participants`),
        api.get<SessionMovie[]>(`/sessions/${found.id}/movies`),
      ]);
      let parts = partsInit;
      setParticipants(parts);
      setMovies(moviesInit);

      let matched = false;

      if (runtimeUserId) {
        matched = parts.some((p) => {
          const pid = p.user_id != null ? String(p.user_id) : `guest:${p.guest_id}`;
          return pid === runtimeUserId;
        });
      }

      if (!matched && userId != null) {
        const self = parts.find((p) => p.user_id === userId);
        if (self) {
          const rid = String(self.user_id);
          setRuntimeUserId(rid);
          matched = true;
        }
      }

      if (!matched && hydrated && !autoJoinAttempted.current) {
        autoJoinAttempted.current = true;
        try {
          const joinResult = await api.post<{ user_id: string; username: string }>(
            `/rooms/${code}/join`,
          );
          setRuntimeUserId(joinResult.user_id);
          if (joinResult.user_id.startsWith("guest:")) {
            setGuest(joinResult.username, joinResult.user_id);
          }
          parts = await api.get<SessionParticipant[]>(
            `/sessions/${found.id}/participants`,
          );
          setParticipants(parts);
        } catch (joinErr) {
          console.error("[LOBBY] Auto-join failed:", joinErr);
          addToast("Не удалось присоединиться к комнате", "error");
          router.push("/");
          return;
        }
      }
    } catch (err) {
      console.error("[LOBBY] fetchSession error:", err);
      addToast("Сессия не найдена", "error");
      router.push("/");
    } finally {
      setLoading(false);
    }
  }, [
    code,
    setSession,
    setParticipants,
    setMovies,
    addToast,
    router,
    runtimeUserId,
    userId,
    guestName,
    setRuntimeUserId,
    setGuest,
    hydrated,
  ]);

  fetchSessionRef.current = fetchSession;

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  useEffect(() => {
    if (!runtimeUserId) {
      return;
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let destroyed = false;
    const DEV = process.env.NODE_ENV !== "production";

    const connect = () => {
      if (destroyed) return;
      const wsBaseUrl = getWsBaseUrl();
      const wsUrl = `${wsBaseUrl}/ws/${code}/${runtimeUserId}${accessToken ? `?token=${accessToken}` : ""}`;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setWsReady(true);
      };

      socket.onclose = (event) => {
        setWsReady(false);
        if (destroyed) return;
        if (event.code === 4001) {
          return;
        }
        if (event.code === 4004) {
          fetchSessionRef.current?.();
          reconnectTimer = setTimeout(connect, 1500);
          return;
        }
        reconnectTimer = setTimeout(connect, 3000);
      };

      socket.onerror = (event) => {
        if (DEV) console.error("[WS] Error:", event);
      };

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "PLAYER_JOINED") {
            addToast(`${msg.payload.username} присоединился`, "info");
            fetchSessionRef.current?.();
          } else if (msg.type === "PLAYER_DISCONNECTED") {
            fetchSessionRef.current?.();
          } else if (
            msg.type === "MOVIE_ADDED" ||
            msg.type === "MOVIE_REMOVED" ||
            msg.type === "MOVIE_SELECTED"
          ) {
            fetchSessionRef.current?.();
          } else if (msg.type === "GAME_STARTED") {
            router.push(`/session/${code}/game-select`);
          } else if (msg.type === "ROOM_STATE") {
            const state = msg.payload as RoomState;
            if (state.status === "playing") {
              router.push(`/session/${code}/game-select`);
            }
          }
        } catch (err) {
          if (DEV) console.error("[WS] Parse error:", err);
        }
      };
    };

    connect();

    const pingInterval = setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "PING" }));
      }
    }, 30000);

    return () => {
      destroyed = true;
      clearInterval(pingInterval);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
      setWsReady(false);
    };
  }, [runtimeUserId, accessToken, code, addToast, router]);

  const handleStartGame = async () => {
    if (!session) return;
    setStarting(true);
    console.log("[START] Starting game for room:", code);
    try {
      const result = await api.post(`/rooms/${code}/start`);
      console.log("[START] POST /rooms/start result:", result);
      router.push(`/session/${code}/game-select`);
    } catch (err) {
      console.error("[START] Error:", err);
      addToast("Не удалось начать игру", "error");
    } finally {
      setStarting(false);
    }
  };

  const handleInvite = async () => {
    const link = `${window.location.origin}/session/${code}`;
    await copyToClipboard(link);
    addToast("Ссылка скопирована", "success");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100dvh-5rem)]">
        <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const isHost = participants.some((p) => {
    const participantRuntimeId = p.user_id != null ? String(p.user_id) : `guest:${p.guest_id}`;
    return p.is_host && participantRuntimeId === runtimeUserId;
  });

  return (
    <div className="flex flex-col min-h-[calc(100dvh-5rem)]">
      <div className="flex-1 px-6 py-5 flex flex-col gap-6">
        {/* Room Title */}
        <h1 className="text-2xl font-bold text-center text-white">
          {code}
        </h1>

        {/* Participants list (scrollable horizontal) */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col items-center gap-1">
            {participants.map((p) => (
              <div
                key={p.id}
                className="flex flex-col items-center gap-3 py-2"
              >
                <Avatar
                  name={p.display_name}
                  size="md"
                  borderColor={p.is_host ? "gray" : "red"}
                />
                <span className="text-white text-xs font-bold text-center">
                  {p.display_name}
                  {(p.user_id != null ? String(p.user_id) : `guest:${p.guest_id}`) === runtimeUserId &&
                    " (ВЫ)"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-4">
          <Button
            variant="secondary"
            className="w-full text-base"
            onClick={handleInvite}
          >
            Пригласить
          </Button>
          {isHost && (
            <Button
              variant="primary"
              className="w-full text-base"
              loading={starting}
              onClick={handleStartGame}
            >
              Начать игру
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
