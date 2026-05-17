"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { useParams, useRouter } from "next/navigation";
import { useUserStore } from "@/stores/user-store";
import { useToastStore } from "@/stores/toast-store";
import { useSessionStore } from "@/stores/session-store";
import { getWsBaseUrl } from "@/lib/constants";
import { api } from "@/lib/api";
import type { FlappyState, FlappyGameOver, FlappyPlayer, FlappyPipe, MovieSearchResult, SessionMovie, GameSession } from "@/types";
import ReconnectingWebSocket from "reconnecting-websocket";

const CANVAS_W = 400;
const CANVAS_H = 600;
const BIRD_R = 15;
const BIRD_W = 34;
const BIRD_H = 24;
const PIPE_W = 52;
const BASE_H = 32;
const GROUND_Y = CANVAS_H - BASE_H;

const BIRD_FRAMES = [
  "/assets/images/FlappyFilms/yellowbird-upflap.png",
  "/assets/images/FlappyFilms/yellowbird-midflap.png",
  "/assets/images/FlappyFilms/yellowbird-downflap.png",
];
const SPRITE_PATHS = {
  bgDay: "/assets/images/FlappyFilms/background-day.png",
  bgNight: "/assets/images/FlappyFilms/background-night.png",
  pipeGreen: "/assets/images/FlappyFilms/pipe-green.png",
  pipeRed: "/assets/images/FlappyFilms/pipe-red.png",
  base: "/assets/images/FlappyFilms/base.png",
  message: "/assets/images/FlappyFilms/message.png",
  gameover: "/assets/images/FlappyFilms/gameover.png",
  digits: Array.from({ length: 10 }, (_, i) => `/assets/images/FlappyFilms/${i}.png`),
};

const COLORS = ["#dc2626", "#3b82f6", "#22c55e", "#eab308", "#a855f7"];

function MovieSelectionModal({
  sessionId,
  onMovieSelected,
}: {
  sessionId: number;
  onMovieSelected: (movie: SessionMovie) => void;
}) {
  const { runtimeUserId } = useUserStore();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [sessionMovies, setSessionMovies] = useState<SessionMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [searched, setSearched] = useState(false);
  const { addToast } = useToastStore();

  useEffect(() => {
    const fetchMovies = async () => {
      try {
        const movies = await api.get<SessionMovie[]>(`/sessions/${sessionId}/movies`);
        setSessionMovies(movies);
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    };
    fetchMovies();
  }, [sessionId]);

  useEffect(() => {
    if (!runtimeUserId) return;
    let cancelled = false;
    const refetch = async () => {
      if (cancelled) return;
      try {
        const updated = await api.get<SessionMovie[]>(
          `/sessions/${sessionId}/movies`,
        );
        if (!cancelled) setSessionMovies(updated);
      } catch {
      }
    };
    const interval = setInterval(refetch, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [runtimeUserId, sessionId]);

  const handleSearch = async () => {
    if (query.trim().length < 2) return;
    setSearched(true);
    setSearching(true);
    try {
      const data = await api.get<MovieSearchResult[]>(
        `/movies/search?query=${encodeURIComponent(query.trim())}`
      );
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleAddMovie = async (movie: MovieSearchResult) => {
    try {
      await api.post(`/sessions/${sessionId}/movies`, {
        kinopoisk_id: movie.kinopoisk_id,
      });
      const updated = await api.get<SessionMovie[]>(`/sessions/${sessionId}/movies`);
      setSessionMovies(updated);
      addToast(`"${movie.title}" добавлен`, "success");
      setQuery("");
      setResults([]);
      setSearched(false);
    } catch {
      addToast("Не удалось добавить фильм", "error");
    }
  };

  const handleSelectMovie = async () => {
    if (selectedId === null) return;
    setConfirming(true);
    try {
      await api.post(`/sessions/${sessionId}/select-movie`, {
        session_movie_id: selectedId,
      });
      const selected = sessionMovies.find((m) => m.id === selectedId);
      if (selected) onMovieSelected(selected);
    } catch {
      addToast("Не удалось выбрать фильм", "error");
    } finally {
      setConfirming(false);
    }
  };

  const [portalNode, setPortalNode] = useState<Element | null>(null);
  useEffect(() => {
    setPortalNode(document.body || document.documentElement);
  }, []);

  if (!portalNode) return null;

  const showEmpty = !loading && !searched && sessionMovies.length === 0;

  return createPortal(
    <div
      className="fixed inset-0 z-[2147483647] overflow-y-auto"
      style={{ background: "#171717" }}
    >
      <div
        style={{
          minHeight: "100dvh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "24px clamp(24px, 6vw, 80px) 140px",
          gap: 28,
        }}
      >
        {/* Search pill */}
        <div
          style={{
            width: "min(100%, 664px)",
            padding: "17px 20px",
            background: "#fff",
            borderRadius: 9999,
            outline: "1px solid #D9D9D9",
            outlineOffset: "-0.5px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Название фильма"
            style={{
              flex: 1,
              minWidth: 0,
              border: "none",
              outline: "none",
              background: "transparent",
              color: "#1E1E1E",
              fontSize: 16,
              fontWeight: 400,
              lineHeight: "20px",
              fontFamily: "'Inter', sans-serif",
            }}
          />
          <button
            onClick={handleSearch}
            aria-label="Искать"
            disabled={searching}
            style={{
              width: 32,
              height: 32,
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {searching ? (
              <span
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  border: "2px solid #ccc",
                  borderTopColor: "#1E1E1E",
                  animation: "spin 0.8s linear infinite",
                }}
              />
            ) : (
              <svg width="22" height="22" viewBox="0 0 16 16" fill="none" aria-hidden>
                <circle cx="7" cy="7" r="5" stroke="#1E1E1E" strokeWidth="1.6" />
                <line x1="10.8" y1="10.8" x2="14" y2="14" stroke="#1E1E1E" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>

        {showEmpty && (
          <div
            style={{
              flex: 1,
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              paddingBottom: "clamp(60px, 20vh, 200px)",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 20,
              }}
            >
              <svg width="60" height="60" viewBox="0 0 16 16" fill="none">
                <circle cx="7" cy="7" r="5" stroke="#E82323" strokeWidth="1.6" />
                <line x1="10.8" y1="10.8" x2="14" y2="14" stroke="#E82323" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              <p
                style={{
                  textAlign: "center",
                  color: "#fff",
                  fontSize: 19,
                  fontWeight: 700,
                  lineHeight: "24px",
                  margin: 0,
                  maxWidth: 420,
                }}
              >
                Начните вводить название фильма и он появится здесь
              </p>
            </div>
          </div>
        )}

        {searched && results.length > 0 && (
          <section
            style={{
              width: "100%",
              maxWidth: 664,
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            <p
              style={{
                color: "rgba(255,255,255,0.5)",
                fontSize: 13,
                fontWeight: 600,
                margin: 0,
              }}
            >
              Результаты поиска — нажмите на карточку чтобы добавить
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                gap: 12,
              }}
            >
              {results.map((m) => (
                <button
                  key={m.kinopoisk_id}
                  onClick={() => handleAddMovie(m)}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    padding: 0,
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "transform 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.03)")}
                  onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                >
                  {m.poster_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={m.poster_url}
                      alt={m.title}
                      style={{
                        width: "100%",
                        aspectRatio: "2/3",
                        objectFit: "cover",
                        borderRadius: 16,
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: "100%",
                        aspectRatio: "2/3",
                        background: "rgba(255,255,255,0.06)",
                        borderRadius: 16,
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
                      fontSize: 13,
                      fontWeight: 600,
                      lineHeight: "16px",
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {m.title}
                  </span>
                  {m.year && (
                    <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 11 }}>
                      {m.year}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </section>
        )}

        {sessionMovies.length > 0 && (
          <section
            style={{
              width: "100%",
              maxWidth: 900,
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            <p
              style={{
                color: "rgba(255,255,255,0.55)",
                fontSize: 14,
                fontWeight: 600,
                margin: 0,
              }}
            >
              Выберите ваш фильм ({sessionMovies.length}):
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                gap: 16,
              }}
            >
              {sessionMovies.map((sm) => {
                const isSelected = selectedId === sm.id;
                return (
                  <button
                    key={sm.id}
                    onClick={() => setSelectedId(sm.id)}
                    style={{
                      position: "relative",
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      padding: 0,
                      borderRadius: 18,
                      border: isSelected
                        ? "3px solid #E82323"
                        : "3px solid transparent",
                      background: "transparent",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {isSelected && (
                      <div
                        style={{
                          position: "absolute",
                          top: 8,
                          right: 8,
                          width: 28,
                          height: 28,
                          borderRadius: "50%",
                          background: "#E82323",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          zIndex: 2,
                        }}
                      >
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                          <path
                            d="M2.5 7L5.5 10L11.5 4"
                            stroke="#fff"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </div>
                    )}
                    {sm.movie?.poster_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={sm.movie.poster_url}
                        alt={sm.movie?.title || ""}
                        style={{
                          width: "100%",
                          aspectRatio: "2/3",
                          objectFit: "cover",
                          borderRadius: 14,
                          opacity: isSelected ? 0.85 : 1,
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          width: "100%",
                          aspectRatio: "2/3",
                          background: "rgba(255,255,255,0.06)",
                          borderRadius: 14,
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
                        fontSize: 13,
                        fontWeight: 600,
                        lineHeight: "16px",
                        padding: "0 2px",
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {sm.movie?.title}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        )}
      </div>

      {selectedId !== null && (
        <div
          style={{
            position: "fixed",
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 10,
            padding: "16px clamp(24px, 6vw, 80px)",
            paddingBottom: "max(16px, env(safe-area-inset-bottom))",
            background: "linear-gradient(transparent, #171717 45%)",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <button
            onClick={handleSelectMovie}
            disabled={confirming}
            style={{
              width: "min(100%, 400px)",
              padding: "18px 0",
              borderRadius: 16,
              background: "#E82323",
              color: "#fff",
              fontWeight: 860,
              fontSize: 17,
              border: "1px solid #6D0C0C",
              cursor: confirming ? "not-allowed" : "pointer",
              opacity: confirming ? 0.6 : 1,
              transition: "all 0.2s",
              boxShadow: "0 8px 32px rgba(232,35,35,0.35)",
              fontFamily: "'SF Pro', 'Inter', sans-serif",
            }}
          >
            {confirming ? "Подтверждение..." : "Подтвердить выбор"}
          </button>
        </div>
      )}
    </div>,
    portalNode
  );
}

export default function FlappyPage() {
  const params = useParams();
  const router = useRouter();
  const code = params.code as string;
  const { runtimeUserId, accessToken } = useUserStore();
  const { addToast } = useToastStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<ReconnectingWebSocket | null>(null);
  const stateRef = useRef<FlappyState | null>(null);
  const [gameOver, setGameOver] = useState<FlappyGameOver | null>(null);
  const [connected, setConnected] = useState(false);
  const [phase, setPhase] = useState<"confirm_wait" | "ready_wait" | "playing" | "game_over">(
    "confirm_wait"
  );
  const [confirmedIds, setConfirmedIds] = useState<string[]>([]);
  const [readyIds, setReadyIds] = useState<string[]>([]);
  const [participantsList, setParticipantsList] = useState<string[]>([]);
  const [readySent, setReadySent] = useState(false);
  const playerId = runtimeUserId;
  const [showMovieSelect, setShowMovieSelect] = useState(true);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [movieSelected, setMovieSelected] = useState(false);
  const spritesRef = useRef<Record<string, HTMLImageElement>>({});
  const spritesLoadedRef = useRef(false);
  const frameCounter = useRef(0);

  const playerColorsRef = useRef<Map<string, string>>(new Map());

  const getPlayerColor = useCallback((pid: string) => {
    const map = playerColorsRef.current;
    if (!map.has(pid)) {
      map.set(pid, COLORS[map.size % COLORS.length]);
    }
    return map.get(pid)!;
  }, []);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const session = await api.get<GameSession>(`/sessions/by-code/${code}`);
        setSessionId(session.id);
      } catch {
        /* ignore */
      }
    };
    fetchSession();
  }, [code]);

  useEffect(() => {
    const sprites: Record<string, HTMLImageElement> = {};
    const allPaths: [string, string][] = [
      ["bgDay", SPRITE_PATHS.bgDay],
      ["bgNight", SPRITE_PATHS.bgNight],
      ["pipeGreen", SPRITE_PATHS.pipeGreen],
      ["pipeRed", SPRITE_PATHS.pipeRed],
      ["base", SPRITE_PATHS.base],
      ["message", SPRITE_PATHS.message],
      ["gameover", SPRITE_PATHS.gameover],
      ...BIRD_FRAMES.map((p, i) => [`bird${i}`, p] as [string, string]),
      ...SPRITE_PATHS.digits.map((p, i) => [`digit${i}`, p] as [string, string]),
    ];

    let loaded = 0;
    const total = allPaths.length;

    allPaths.forEach(([key, path]) => {
      const img = new Image();
      img.src = path;
      img.onload = () => {
        loaded++;
        if (loaded >= total) spritesLoadedRef.current = true;
      };
      img.onerror = () => {
        loaded++;
        if (loaded >= total) spritesLoadedRef.current = true;
      };
      sprites[key] = img;
    });

    spritesRef.current = sprites;
  }, []);

  const handleMovieSelected = () => {
    setMovieSelected(true);
    setShowMovieSelect(false);
  };

  useEffect(() => {
    if (!playerId || !movieSelected) return;

    const wsBaseUrl = getWsBaseUrl();
    const wsUrl = `${wsBaseUrl}/ws/game/flappy/${code}${accessToken ? `?token=${accessToken}` : ""}`;
    const ws = new ReconnectingWebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "state") {
          stateRef.current = msg as FlappyState;
          const s = msg as FlappyState;
          if (s.phase) setPhase(s.phase);
          else if (s.running) setPhase("playing");
          if (s.confirmed_ids) setConfirmedIds(s.confirmed_ids);
          if (s.ready_ids) setReadyIds(s.ready_ids);
          if (s.participants) setParticipantsList(s.participants);
          if (s.ready_ids && playerId && !s.ready_ids.includes(playerId)) {
            setReadySent(false);
          }
        } else if (msg.type === "game_over") {
          setGameOver(msg as FlappyGameOver);
          setPhase("game_over");
        }
      } catch {
      }
    };

    return () => {
      ws.close();
    };
  }, [code, playerId, accessToken, movieSelected]);

  useEffect(() => {
    if (!movieSelected) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let baseScroll = 0;

    const drawDigits = (num: number, cx: number, cy: number) => {
      const s = spritesRef.current;
      const str = String(num);
      const digitW = 14;
      const digitH = 20;
      const totalW = str.length * (digitW + 2) - 2;
      let x = cx - totalW / 2;
      for (const ch of str) {
        const img = s[`digit${ch}`];
        if (img && img.complete && img.naturalWidth > 0) {
          ctx.drawImage(img, x, cy - digitH / 2, digitW, digitH);
        }
        x += digitW + 2;
      }
    };

    const draw = () => {
      frameCounter.current++;
      const s = spritesRef.current;

      const bg = s.bgDay;
      if (bg && bg.complete && bg.naturalWidth > 0) {
        ctx.drawImage(bg, 0, 0, CANVAS_W, CANVAS_H);
      } else {
        ctx.fillStyle = "#70c5ce";
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
      }

      const state = stateRef.current;
      if (!state || !state.running) {
        const msgImg = s.message;
        if (msgImg && msgImg.complete && msgImg.naturalWidth > 0 && !state) {
          const mw = 184;
          const mh = 267;
          ctx.drawImage(msgImg, (CANVAS_W - mw) / 2, (CANVAS_H - mh) / 2 - 30, mw, mh);
        } else {
          ctx.textAlign = "center";
          
          if (!state) {
            ctx.fillStyle = "rgba(255,255,255,0.5)";
            ctx.font = "bold 14px 'Press Start 2P', monospace";
            ctx.fillText("ПОДКЛЮЧЕНИЕ К СЕРВЕРУ...", CANVAS_W / 2, CANVAS_H / 2);
          } else {
            const pulse = 0.6 + Math.sin(frameCounter.current / 10) * 0.4;
            ctx.fillStyle = `rgba(232, 35, 35, ${pulse})`;
            ctx.font = "bold 20px 'Press Start 2P', monospace";
            ctx.fillText("ОЖИДАНИЕ", CANVAS_W / 2, CANVAS_H / 2 - 20);
            
            ctx.fillStyle = "rgba(255,255,255,0.8)";
            ctx.font = "bold 12px 'Press Start 2P', monospace";
            ctx.fillText("ДРУГИХ ИГРОКОВ...", CANVAS_W / 2, CANVAS_H / 2 + 15);

            Object.entries(state.players).forEach(([pid, p]: [string, FlappyPlayer]) => {
                const birdFrameIdx = Math.floor(frameCounter.current / 8) % 3;
                const birdImg = s[`bird${birdFrameIdx}`];
                const bx = 80;
                const by = p.y;
                if (birdImg && birdImg.complete) {
                    ctx.save();
                    ctx.translate(bx, by);
                    if (pid !== playerId) ctx.globalAlpha = 0.3 + Math.sin(frameCounter.current / 15) * 0.2;
                    ctx.drawImage(birdImg, -BIRD_W / 2, -BIRD_H / 2, BIRD_W, BIRD_H);
                    ctx.restore();
                }
            });
          }
        }

        const baseImg = s.base;
        if (baseImg && baseImg.complete && baseImg.naturalWidth > 0) {
          const bw = baseImg.naturalWidth;
          for (let bx = -baseScroll % bw; bx < CANVAS_W; bx += bw) {
            ctx.drawImage(baseImg, bx, GROUND_Y, bw, BASE_H);
          }
        }

        animId = requestAnimationFrame(draw);
        return;
      }

      state.pipes.forEach((pipe: FlappyPipe) => {
        const pipeImg = s.pipeGreen;
        if (pipeImg && pipeImg.complete && pipeImg.naturalWidth > 0) {
          const pipeH = pipeImg.naturalHeight;
          const pw = pipe.width || PIPE_W;

          const gapTop = pipe.gap_y;
          const gapBottom = pipe.gap_y + (pipe.gap_height || 120);

          ctx.save();
          ctx.translate(pipe.x + pw / 2, gapTop);
          ctx.scale(1, -1);
          ctx.drawImage(pipeImg, -pw / 2, 0, pw, pipeH);
          ctx.restore();

          ctx.drawImage(pipeImg, pipe.x, gapBottom, pw, pipeH);
        } else {
          ctx.fillStyle = "#22c55e";
          const gapTop = pipe.gap_y;
          const gapBottom = pipe.gap_y + (pipe.gap_height || 120);
          ctx.fillRect(pipe.x, 0, pipe.width || PIPE_W, gapTop);
          ctx.fillRect(pipe.x, gapBottom, pipe.width || PIPE_W, CANVAS_H - gapBottom);
        }
      });

      if (state.running) {
        baseScroll += 2.5;
      }

      const baseImg = s.base;
      if (baseImg && baseImg.complete && baseImg.naturalWidth > 0) {
        const bw = baseImg.naturalWidth;
        for (let bx = -(baseScroll % bw); bx < CANVAS_W; bx += bw) {
          ctx.drawImage(baseImg, bx, GROUND_Y, bw, BASE_H);
        }
      } else {
        ctx.fillStyle = "#ded895";
        ctx.fillRect(0, GROUND_Y, CANVAS_W, BASE_H);
      }

      const players = state.players;
      Object.entries(players).forEach(([pid, p]: [string, FlappyPlayer]) => {
        const birdFrameIdx = Math.floor(frameCounter.current / 8) % 3;
        const birdImg = s[`bird${birdFrameIdx}`];

        const bx = 80;
        const by = p.y;

        if (birdImg && birdImg.complete && birdImg.naturalWidth > 0 && p.alive) {
          const angle = Math.min(Math.max(p.velocity * 3, -30), 90) * (Math.PI / 180);
          ctx.save();
          ctx.translate(bx, by);
          ctx.rotate(angle);

          if (pid !== playerId) {
            ctx.globalAlpha = 0.6;
          }
          ctx.drawImage(birdImg, -BIRD_W / 2, -BIRD_H / 2, BIRD_W, BIRD_H);
          ctx.globalAlpha = 1;
          ctx.restore();
        } else {
          const color = getPlayerColor(pid);
          ctx.fillStyle = p.alive ? color : "#555";
          ctx.beginPath();
          ctx.arc(bx, by, BIRD_R, 0, Math.PI * 2);
          ctx.fill();
        }

        if (pid === playerId) {
          ctx.fillStyle = "#fff";
          ctx.font = "bold 10px Inter, sans-serif";
          ctx.textAlign = "center";
          ctx.strokeStyle = "rgba(0,0,0,0.6)";
          ctx.lineWidth = 3;
          ctx.strokeText("ВЫ", bx, by + BIRD_H / 2 + 14);
          ctx.fillText("ВЫ", bx, by + BIRD_H / 2 + 14);
        }
      });

      const myPlayer = players[playerId ?? ""];
      if (myPlayer) {
        drawDigits(myPlayer.score, CANVAS_W / 2, 50);
      }

      if (!state.running) {
        ctx.fillStyle = "rgba(0,0,0,0.45)";
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

        const goImg = s.gameover;
        if (goImg && goImg.complete && goImg.naturalWidth > 0) {
          const gw = goImg.naturalWidth * 2;
          const gh = goImg.naturalHeight * 2;
          ctx.drawImage(goImg, (CANVAS_W - gw) / 2, (CANVAS_H - gh) / 2 - 20, gw, gh);
        } else {
          ctx.fillStyle = "#fff";
          ctx.font = "bold 28px Inter, sans-serif";
          ctx.textAlign = "center";
          ctx.fillText("Нажмите, чтобы прыгнуть!", CANVAS_W / 2, CANVAS_H / 2);
        }
      }

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => cancelAnimationFrame(animId);
  }, [playerId, getPlayerColor, movieSelected]);

  const handleJump = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && playerId) {
      ws.send(JSON.stringify({ action: "jump", player_id: playerId }));
    }
  }, [playerId]);

  useEffect(() => {
    if (!movieSelected) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space" || e.code === "ArrowUp") {
        const target = e.target as HTMLElement | null;
        const tag = target?.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea" || target?.isContentEditable) {
          return;
        }
        e.preventDefault();
        handleJump();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [movieSelected, handleJump]);

  const handleReady = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !playerId) return;
    ws.send(JSON.stringify({ action: "ready", player_id: playerId }));
    setReadySent(true);
  }, [playerId]);

  if (showMovieSelect && sessionId === null) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 100,
          background: "#1A1A1A",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 9999,
            border: "3px solid rgba(232,35,35,0.25)",
            borderTopColor: "#E82323",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14 }}>
          Загрузка сессии...
        </p>
      </div>
    );
  }

  if (showMovieSelect && sessionId) {
    return (
      <MovieSelectionModal
        sessionId={sessionId}
        onMovieSelected={handleMovieSelected}
      />
    );
  }

  if (gameOver) {
    const isWinner = gameOver.winner_id === playerId;
    const scores = Object.entries(gameOver.scores).sort(
      ([, a], [, b]) => b - a
    );

    return (
      <div className="flex flex-col min-h-[calc(100dvh-5rem)] items-center justify-center px-6 gap-8">
        <h1 className="text-3xl font-bold text-white">
          {isWinner ? "Вы победили! 🎉" : "Игра окончена"}
        </h1>
        <div className="flex flex-col gap-3 w-full max-w-xs">
          {scores.map(([pid, score], i) => (
            <div
              key={pid}
              className={`flex justify-between items-center p-4 rounded-2xl ${
                pid === gameOver.winner_id
                  ? "bg-red-600/20 ring-1 ring-red-600"
                  : "bg-white/5"
              }`}
            >
              <span className="text-white font-bold">
                #{i + 1} {pid === playerId ? "ВЫ" : pid.slice(0, 8)}
              </span>
              <span className="text-neutral-300">{score} очков</span>
            </div>
          ))}
        </div>
        <button
          onClick={() => router.push(`/session/${code}/result`)}
          className="px-8 py-3 bg-red-600 text-white rounded-full font-bold text-lg shadow-lg"
        >
          К результатам
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col min-h-[calc(100dvh-5rem)] items-center justify-center bg-neutral-900 relative"
      onClick={handleJump}
      onTouchStart={handleJump}
    >
      {/* Connection indicator */}
      <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
        <div
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`}
        />
        <span className="text-xs text-neutral-400">
          {connected ? "Online" : "Connecting..."}
        </span>
      </div>

      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        className="rounded-2xl border border-neutral-700 w-full max-w-[400px] h-auto"
        style={{ touchAction: "none", aspectRatio: `${CANVAS_W} / ${CANVAS_H}` }}
      />

      <p className="text-neutral-500 text-sm mt-4">
        Нажмите, коснитесь экрана или Space, чтобы прыгнуть
      </p>

      {/* Bug 4a fix: block the gameplay until every participant has
          confirmed their movie. */}
      {phase === "confirm_wait" && (
        <div
          className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-4 bg-black/70"
          onClick={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
        >
          <div className="w-10 h-10 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
          <h2 className="text-xl font-bold text-white">
            Ожидание подтверждения
          </h2>
          <p className="text-neutral-300 text-sm">
            Подтвердили выбор: {confirmedIds.length} / {Math.max(participantsList.length, confirmedIds.length || 2)}
          </p>
          <p className="text-neutral-500 text-xs max-w-xs text-center">
            Игра начнётся, когда все игроки выберут и подтвердят фильм.
          </p>
        </div>
      )}

      {/* Bug 4b fix: after everyone confirmed, wait for Ready from each
          player before starting the game. */}
      {phase === "ready_wait" && (
        <div
          className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-5 bg-black/80"
          onClick={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
        >
          <h2 className="text-2xl font-bold text-white">Готовы к старту?</h2>
          <p className="text-neutral-300 text-sm">
            Готовы: {readyIds.length} / {Math.max(participantsList.length, readyIds.length || 2)}
          </p>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleReady();
            }}
            disabled={readySent || (playerId != null && readyIds.includes(playerId))}
            className="px-12 py-4 bg-red-600 text-white rounded-full font-bold text-xl shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              minWidth: 240,
              fontSize: 19,
              fontWeight: 860,
              fontFamily: "'SF Pro', 'Inter', sans-serif",
              letterSpacing: "0.01em",
            }}
          >
            {readySent || (playerId != null && readyIds.includes(playerId))
              ? "Ожидаем остальных..."
              : "Готов"}
          </button>
          <p className="text-neutral-500 text-xs max-w-xs text-center">
            Игра начнётся сразу после того, как все нажмут «Готов».
          </p>
        </div>
      )}
    </div>
  );
}
