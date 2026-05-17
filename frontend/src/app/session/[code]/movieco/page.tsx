"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useUserStore } from "@/stores/user-store";
import { useGameStore } from "@/stores/game-store";
import { useToastStore } from "@/stores/toast-store";
import { getWsBaseUrl } from "@/lib/constants";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import Image from "next/image";
import { motion } from "framer-motion";
import { copyToClipboard } from "@/lib/utils";
import type {
  GameSession,
  SessionMovie,
  SessionParticipant,
  TournamentRoomState,
  TournamentRoomCreated,
  TournamentMovieCard,
} from "@/types";
import ReconnectingWebSocket from "reconnecting-websocket";

export default function MovieCOPage() {
  const params = useParams();
  const router = useRouter();
  const code = params.code as string;
  const { userId, username, guestName, runtimeUserId } = useUserStore();
  const { userKey, setUserKey, setTournamentState } = useGameStore();
  const { addToast } = useToastStore();
  const wsRef = useRef<ReconnectingWebSocket | null>(null);

  const [roomState, setRoomState] = useState<TournamentRoomState | null>(null);
  const [roomId, setRoomId] = useState<number | null>(null);
  const [step, setStep] = useState<"init" | "lobby" | "voting" | "finished">(
    "init"
  );
  const [voting, setVoting] = useState(false);
  const [lobbyMovies, setLobbyMovies] = useState<SessionMovie[]>([]);
  const [isSessionHost, setIsSessionHost] = useState(false);

  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    if (useUserStore.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsub = useUserStore.persist.onFinishHydration(() => setHydrated(true));
    return unsub;
  }, []);

  const initCalled = useRef(false);

  const displayName =
    username ||
    guestName ||
    `Player-${(runtimeUserId || (userId ? String(userId) : "anon")).slice(0, 6)}`;

  const storageKey = `movieco:connection:${code}:${runtimeUserId || "anon"}`;

  const saveConnection = (nextRoomId: number, nextUserKey: string) => {
    if (typeof window === "undefined") return;
    localStorage.setItem(
      storageKey,
      JSON.stringify({ roomId: nextRoomId, userKey: nextUserKey }),
    );
  };

  const loadConnection = (): { roomId: number; userKey: string } | null => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as { roomId?: number; userKey?: string };
      if (typeof parsed.roomId === "number" && typeof parsed.userKey === "string") {
        return { roomId: parsed.roomId, userKey: parsed.userKey };
      }
    } catch {
    }
    return null;
  };

  const clearConnection = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(storageKey);
  };

  useEffect(() => {
    if (!hydrated || !runtimeUserId) return;

    if (initCalled.current) return;
    initCalled.current = true;

    let cancelled = false;

    const sleep = (ms: number) => new Promise<void>((resolve) => {
      setTimeout(resolve, ms);
    });

    const findExistingRoom = async (): Promise<{ room_id: number; title: string; status: string } | undefined> => {
      for (const st of ["LOBBY", "RUNNING"]) {
        const rooms = await api.get<{ room_id: number; title: string; status: string }[]>(
          `/tournaments/rooms?status=${st}&limit=50`
        );
        const match = rooms.find((r) => r.title === `Session ${code}`);
        if (match) return match;
      }
      return undefined;
    };

    const applyJoinedRoom = (joined: {
      room_id: number;
      user_key: string;
      room: TournamentRoomState;
    }) => {
      if (cancelled) return;
      setRoomId(joined.room_id);
      setUserKey(joined.user_key);
      setRoomState(joined.room);
      setTournamentState(joined.room);
      saveConnection(joined.room_id, joined.user_key);
      setStep(
        joined.room.status === "RUNNING"
          ? "voting"
          : joined.room.status === "FINISHED"
            ? "finished"
            : "lobby"
      );
    };

    const tryRestoreConnection = async (): Promise<boolean> => {
      const saved = loadConnection();
      if (!saved) return false;
      try {
        const state = await api.get<TournamentRoomState>(`/tournaments/rooms/${saved.roomId}`);
        const belongsToRoom = state.participants.some((p) => p.user_key === saved.userKey);
        if (!belongsToRoom) {
          clearConnection();
          return false;
        }
        if (cancelled) return true;
        setRoomId(saved.roomId);
        setUserKey(saved.userKey);
        setRoomState(state);
        setTournamentState(state);
        setStep(
          state.status === "RUNNING"
            ? "voting"
            : state.status === "FINISHED"
              ? "finished"
              : "lobby"
        );
        return true;
      } catch {
        clearConnection();
        return false;
      }
    };

    const resolveSessionRole = async (): Promise<"host" | "participant" | "unknown"> => {
      if (!runtimeUserId) return "unknown";
      try {
        const session = await api.get<GameSession>(`/sessions/by-code/${code}`);
        const parts = await api.get<SessionParticipant[]>(
          `/sessions/${session.id}/participants`
        );
        const self = parts.find((p) => {
          const pid = p.user_id != null ? String(p.user_id) : `guest:${p.guest_id}`;
          return pid === runtimeUserId;
        });
        if (!self) return "unknown";
        return self.is_host ? "host" : "participant";
      } catch {
        return "unknown";
      }
    };

    const joinRoomById = async (targetRoomId: number) => {
      const joined = await api.post<{ room_id: number; user_key: string; room: TournamentRoomState }>(
        `/tournaments/rooms/${targetRoomId}/join`,
        { display_name: displayName }
      );
      applyJoinedRoom(joined);
    };

    const init = async () => {
      try {
        const role = await resolveSessionRole();
        if (!cancelled && role === "host") setIsSessionHost(true);

        if (await tryRestoreConnection()) {
          return;
        }

        const existing = await findExistingRoom();

        if (existing) {
          await joinRoomById(existing.room_id);
          return;
        }

        if (role === "participant") {
          for (let attempt = 0; attempt < 12; attempt += 1) {
            await sleep(1000);
            if (cancelled) return;
            const waited = await findExistingRoom();
            if (waited) {
              await joinRoomById(waited.room_id);
              return;
            }
          }
          addToast("Хост еще не создал комнату MovieCO", "error");
          router.push(`/session/${code}`);
          return;
        }

        const session = await api.get<GameSession>(`/sessions/by-code/${code}`);
        const sessionMovies = await api.get<SessionMovie[]>(
          `/sessions/${session.id}/movies`,
        );

        if (sessionMovies.length < 2) {
          addToast("Добавьте минимум 2 фильма для MovieCO", "error");
          router.push(`/session/${code}/movies?next=movieco`);
          return;
        }

        const created = await api.post<TournamentRoomCreated & { user_key: string; room: TournamentRoomState }>(
          "/tournaments/rooms",
          {
            title: `Session ${code}`,
            display_name: displayName,
            bracket_size: Math.min(16, Math.max(2, sessionMovies.length)),
            session_movie_ids: sessionMovies.map((sm) => sm.movie_id),
          }
        );
        applyJoinedRoom(created);
      } catch (err) {
        console.error("[MovieCO] init error:", err);
        if (!cancelled) {
          addToast("Ошибка подключения к турниру", "error");
          router.push(`/session/${code}`);
        }
      }
    };
    init();

    return () => {
      cancelled = true;
    };
  }, [
    code,
    runtimeUserId,
    hydrated,
    addToast,
    setUserKey,
    setTournamentState,
    router,
  ]);

  useEffect(() => {
    if (!roomId || !userKey) return;

    const wsBaseUrl = getWsBaseUrl();
    const wsUrl = `${wsBaseUrl}/tournaments/ws/${roomId}?user_key=${userKey}`;
    const ws = new ReconnectingWebSocket(wsUrl);
    wsRef.current = ws;

    ws.onclose = (event) => {
      if (event.code === 4003 || event.code === 4004) {
        clearConnection();
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "room_state" || msg.type === "vote_accepted") {
          const state = msg.payload as TournamentRoomState;
          setRoomState(state);
          setTournamentState(state);

          if (state.status === "RUNNING") {
            setStep("voting");
          } else if (state.status === "FINISHED") {
            setStep("finished");
          }
        } else if (msg.type === "pong") {
        } else if (msg.type === "error") {
          addToast(msg.payload?.detail || "Ошибка", "error");
        }
      } catch {
      }
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000);

    const pollInterval = setInterval(async () => {
      try {
        const state = await api.get<TournamentRoomState>(`/tournaments/rooms/${roomId}`);
        setRoomState(state);
        setTournamentState(state);
        if (state.status === "RUNNING") {
          setStep("voting");
        } else if (state.status === "FINISHED") {
          setStep("finished");
        }
      } catch {
      }
    }, 2500);

    return () => {
      clearInterval(pingInterval);
      clearInterval(pollInterval);
      ws.close();
    };
  }, [roomId, userKey, addToast, setTournamentState]);

  useEffect(() => {
    if (step !== "lobby") return;
    let cancelled = false;
    const fetchMovies = async () => {
      try {
        const session = await api.get<GameSession>(`/sessions/by-code/${code}`);
        const movies = await api.get<SessionMovie[]>(
          `/sessions/${session.id}/movies`,
        );
        if (!cancelled) setLobbyMovies(movies);
      } catch {
      }
    };
    fetchMovies();
    const iv = setInterval(fetchMovies, 3000);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, [step, code]);

  const handleInvite = async () => {
    const link = `${window.location.origin}/session/${code}`;
    await copyToClipboard(link);
    addToast("Ссылка скопирована", "success");
  };

  const handleStartTournament = async () => {
    if (!roomId || !userKey) return;
    try {
      await api.post(`/tournaments/rooms/${roomId}/start?user_key=${userKey}`);
    } catch {
      addToast("Не удалось запустить турнир", "error");
    }
  };

  const handleVote = async (movieId: number) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    setVoting(true);
    ws.send(JSON.stringify({ type: "vote", movie_id: movieId }));
    setTimeout(() => setVoting(false), 500);
  };

  if (step === "init") {
    return (
      <div className="flex items-center justify-center min-h-[calc(100dvh-5rem)]">
        <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (step === "lobby" && roomState) {
    const iAmHost = isSessionHost;

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          minHeight: "calc(100dvh - 5.5rem)",
          alignItems: "center",
          padding: "24px clamp(20px, 5vw, 40px) 100px",
          gap: 36,
        }}
      >
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 220, damping: 22 }}
          style={{
            color: "#fff",
            fontSize: 26,
            fontWeight: 700,
            textAlign: "center",
            margin: 0,
            fontFamily: "'SF Pro', 'Inter', sans-serif",
          }}
        >
          {code}
        </motion.h1>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            alignItems: "flex-start",
            gap: 24,
            width: "100%",
          }}
        >
          {roomState.participants.map((p) => (
            <div
              key={p.id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
                minWidth: 76,
              }}
            >
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  background: p.is_host ? "#E82323" : "#525252",
                  color: "#fff",
                  fontWeight: 800,
                  fontSize: 18,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  outline: "2px solid rgba(255,255,255,0.08)",
                }}
              >
                {p.display_name.slice(0, 1).toUpperCase()}
              </div>
              <span
                style={{
                  color: "#fff",
                  fontSize: 12,
                  fontWeight: 700,
                  textAlign: "center",
                  maxWidth: 100,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {p.display_name}
                {p.is_host && " ★"}
              </span>
            </div>
          ))}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
            gap: 16,
            width: "100%",
            maxWidth: 720,
          }}
        >
          {lobbyMovies.length === 0 ? (
            <p
              style={{
                gridColumn: "1 / -1",
                textAlign: "center",
                color: "rgba(255,255,255,0.5)",
                fontSize: 14,
                margin: 0,
              }}
            >
              Фильмы ещё не добавлены
            </p>
          ) : (
            lobbyMovies.map((sm) => (
              <div
                key={sm.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                {sm.movie?.poster_url ? (
                  <div
                    style={{
                      position: "relative",
                      width: "100%",
                      aspectRatio: "2/3",
                      borderRadius: 24,
                      overflow: "hidden",
                    }}
                  >
                    <Image
                      src={sm.movie.poster_url}
                      alt={sm.movie?.title || "Movie"}
                      fill
                      sizes="120px"
                      className="object-cover"
                    />
                  </div>
                ) : (
                  <div
                    style={{
                      width: "100%",
                      aspectRatio: "2/3",
                      background: "rgba(255,255,255,0.06)",
                      borderRadius: 24,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 28,
                    }}
                  >
                    🎬
                  </div>
                )}
                <span
                  style={{
                    color: "#fff",
                    fontSize: 12,
                    fontWeight: 700,
                    textAlign: "center",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    lineHeight: "16px",
                  }}
                >
                  {sm.movie?.title}
                </span>
              </div>
            ))
          )}
        </div>

        <div
          style={{
            width: "min(100%, 330px)",
            display: "flex",
            flexDirection: "column",
            gap: 16,
            marginTop: "auto",
          }}
        >
          <button
            onClick={handleInvite}
            style={{
              width: "100%",
              height: 60,
              background: "#fff",
              color: "#1A1A1A",
              fontSize: 17,
              fontWeight: 860,
              fontFamily: "'SF Pro', 'Inter', sans-serif",
              borderRadius: 16,
              border: "1px solid #6D0C0C",
              cursor: "pointer",
              boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
            }}
          >
            Пригласить
          </button>

          {iAmHost ? (
            <button
              onClick={handleStartTournament}
              style={{
                width: "100%",
                height: 60,
                background: "#E82323",
                color: "#fff",
                fontSize: 17,
                fontWeight: 860,
                fontFamily: "'SF Pro', 'Inter', sans-serif",
                borderRadius: 16,
                border: "1px solid #6D0C0C",
                cursor: "pointer",
                boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
              }}
            >
              Начать игру
            </button>
          ) : (
            <p
              style={{
                color: "rgba(255,255,255,0.5)",
                fontSize: 14,
                textAlign: "center",
                margin: 0,
              }}
            >
              Ожидание запуска турнира хостом…
            </p>
          )}
        </div>
      </div>
    );
  }

  if (step === "voting" && roomState && roomState.current_match) {
    const match = roomState.current_match;

    return (
      <div className="flex flex-col min-h-[calc(100dvh-5rem)] px-6 py-8 gap-6">
        <div className="text-center">
          <h2 className="text-lg font-bold text-white">{roomState.round_name}</h2>
          <Progress value={roomState.progress * 100} className="mt-2" />
        </div>

        <div className="flex-1 flex flex-col gap-6 justify-center">
          <p className="text-center text-neutral-400 text-sm font-bold">
            Выберите фильм
          </p>

          <div className="grid grid-cols-2 gap-4">
            <VoteCard
              movie={match.left}
              onVote={() => handleVote(match.left.movie_id)}
              disabled={voting}
            />
            <VoteCard
              movie={match.right}
              onVote={() => handleVote(match.right.movie_id)}
              disabled={voting}
            />
          </div>
        </div>

        <p className="text-center text-neutral-600 text-xs">
          Матч {match.match_no + 1} · Раунд {match.round_no + 1}
        </p>
      </div>
    );
  }

  if (step === "finished" && roomState) {
    const winner = roomState.winner;
    return (
      <div className="flex flex-col min-h-[calc(100dvh-5rem)] items-center justify-center px-6 gap-8">
        <h1 className="text-2xl font-bold text-white">Победитель!</h1>
        {winner && (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex flex-col items-center gap-4"
          >
            {winner.poster_url && (
              <Image
                src={winner.poster_url}
                alt={winner.title}
                width={200}
                height={300}
                className="rounded-[30px] shadow-lg w-full max-w-[200px] h-auto"
              />
            )}
            <h2 className="text-xl font-bold text-white">{winner.title}</h2>
            {winner.year && (
              <p className="text-neutral-400">{winner.year}</p>
            )}
            {winner.rating && (
              <div className="px-3 py-1 bg-red-600 rounded-full text-sm font-bold">
                ★ {winner.rating}
              </div>
            )}
          </motion.div>
        )}
        <Button
          variant="primary"
          onClick={() => router.push(`/session/${code}/result`)}
        >
          К результатам
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100dvh-5rem)]">
      <p className="text-neutral-400">Загрузка...</p>
    </div>
  );
}

function VoteCard({
  movie,
  onVote,
  disabled,
}: {
  movie: TournamentMovieCard;
  onVote: () => void;
  disabled: boolean;
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.95 }}
      onClick={onVote}
      disabled={disabled}
      className="flex flex-col items-center gap-3 p-3 bg-white/5 rounded-[30px] hover:bg-white/10 transition-colors disabled:opacity-50"
    >
      {movie.poster_url ? (
        <Image
          src={movie.poster_url}
          alt={movie.title}
          width={140}
          height={210}
          className="w-full aspect-[2/3] rounded-2xl object-cover"
        />
      ) : (
        <div className="w-full aspect-[2/3] bg-neutral-700 rounded-2xl flex items-center justify-center">
          <span className="text-3xl">🎬</span>
        </div>
      )}
      <span className="text-white text-sm font-bold text-center line-clamp-2">
        {movie.title}
      </span>
      {movie.year && (
        <span className="text-neutral-400 text-xs">{movie.year}</span>
      )}
    </motion.button>
  );
}
