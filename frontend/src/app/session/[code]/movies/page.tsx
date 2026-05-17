"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X } from "lucide-react";
import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session-store";
import { useToastStore } from "@/stores/toast-store";
import { useUserStore } from "@/stores/user-store";
import { Button } from "@/components/ui/button";
import type { GameSession, MovieSearchResult, SessionMovie } from "@/types";

function SearchPill({
  value,
  onChange,
  onSubmit,
  searching,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  searching: boolean;
}) {
  return (
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
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
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
        onClick={onSubmit}
        aria-label="Искать"
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
            <line
              x1="10.8"
              y1="10.8"
              x2="14"
              y2="14"
              stroke="#1E1E1E"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        )}
      </button>
    </div>
  );
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1, type: "spring", stiffness: 200, damping: 22 }}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 20,
      }}
    >
      <div
        aria-hidden
        style={{
          width: 80,
          height: 80,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="60" height="60" viewBox="0 0 16 16" fill="none">
          <circle cx="7" cy="7" r="5" stroke="#E82323" strokeWidth="1.6" />
          <line
            x1="10.8"
            y1="10.8"
            x2="14"
            y2="14"
            stroke="#E82323"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </div>
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
    </motion.div>
  );
}

export default function SessionMoviesPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = params.code as string;
  const nextGame = searchParams.get("next");

  const { addToast } = useToastStore();
  const { setSession, movies, setMovies } = useSessionStore();
  const { runtimeUserId, accessToken } = useUserStore();

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searched, setSearched] = useState(false);

  const refetchMoviesRef = useRef<(() => Promise<void>) | undefined>(undefined);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const found = await api.get<GameSession>(`/sessions/by-code/${code}`);
        if (!found) {
          addToast("Сессия не найдена", "error");
          router.push("/");
          return;
        }
        setSession(found);
        setSessionId(found.id);
        setMovies(await api.get<SessionMovie[]>(`/sessions/${found.id}/movies`));
      } catch {
        addToast("Ошибка загрузки", "error");
      } finally {
        setLoading(false);
      }
    };
    fetchSession();
  }, [code, setSession, setMovies, addToast, router]);

  refetchMoviesRef.current = useCallback(async () => {
    if (sessionId == null) return;
    try {
      setMovies(await api.get<SessionMovie[]>(`/sessions/${sessionId}/movies`));
    } catch {
      /* ignore */
    }
  }, [sessionId, setMovies]);

  useEffect(() => {
    if (!runtimeUserId || sessionId == null) return;
    const interval = setInterval(() => {
      refetchMoviesRef.current?.();
    }, 3000);
    return () => clearInterval(interval);
  }, [runtimeUserId, sessionId]);

  const handleSearch = useCallback(async () => {
    if (query.trim().length < 2) return;
    setSearched(true);
    setSearching(true);
    try {
      const data = await api.get<MovieSearchResult[]>(
        `/movies/search?query=${encodeURIComponent(query.trim())}`,
      );
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, [query]);

  const handleAddMovie = async (m: MovieSearchResult) => {
    if (!sessionId) return;
    try {
      await api.post(`/sessions/${sessionId}/movies`, {
        kinopoisk_id: m.kinopoisk_id,
      });
      setMovies(await api.get<SessionMovie[]>(`/sessions/${sessionId}/movies`));
      addToast(`«${m.title}» добавлен`, "success");
    } catch {
      addToast("Не удалось добавить фильм", "error");
    }
  };

  const handleRemoveMovie = async (sessionMovieId: number) => {
    if (!sessionId) return;
    try {
      await api.delete(`/sessions/${sessionId}/movies/${sessionMovieId}`);
      setMovies(await api.get<SessionMovie[]>(`/sessions/${sessionId}/movies`));
      addToast("Фильм удалён", "success");
    } catch {
      addToast("Не удалось удалить фильм", "error");
    }
  };

  const handleContinue = () => {
    if (nextGame === "movieco") router.push(`/session/${code}/movieco`);
    else if (nextGame === "flappy") router.push(`/session/${code}/flappy`);
    else router.push(`/session/${code}`);
  };

  if (loading) {
    return (
      <div
        style={{
          minHeight: "calc(100dvh - 5.5rem)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            border: "2px solid rgba(232,35,35,0.25)",
            borderTopColor: "#E82323",
            animation: "spin 0.8s linear infinite",
          }}
        />
      </div>
    );
  }

  const hasAny = movies.length > 0 || results.length > 0;
  const showEmpty = !searched && movies.length === 0;

  return (
    <div
      style={{
        minHeight: "calc(100dvh - 5.5rem)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "24px clamp(24px, 6vw, 80px) 100px",
        gap: 28,
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 220, damping: 22 }}
        style={{ width: "100%", display: "flex", justifyContent: "center" }}
      >
        <SearchPill
          value={query}
          onChange={setQuery}
          onSubmit={handleSearch}
          searching={searching}
        />
      </motion.div>

      {showEmpty && !hasAny && (
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
          <EmptyState />
        </div>
      )}

      <AnimatePresence>
        {searched && (
          <motion.section
            key="results"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ type: "spring", stiffness: 220, damping: 24 }}
            style={{ width: "100%", maxWidth: 664, display: "flex", flexDirection: "column", gap: 14 }}
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
            {results.length === 0 && !searching ? (
              <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 14, fontWeight: 500, margin: 0 }}>
                Ничего не нашли, попробуйте другое название
              </p>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                  gap: 12,
                }}
              >
                {results.map((m) => (
                  <motion.button
                    key={m.kinopoisk_id}
                    whileHover={{ scale: 1.04, y: -3 }}
                    whileTap={{ scale: 0.97 }}
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
                    }}
                  >
                    {m.poster_url ? (
                      <div style={{ position: "relative", width: "100%", aspectRatio: "2/3", borderRadius: 16, overflow: "hidden" }}>
                        <Image src={m.poster_url} alt={m.title} fill sizes="160px" className="object-cover" />
                      </div>
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
                      <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 11 }}>{m.year}</span>
                    )}
                  </motion.button>
                ))}
              </div>
            )}
          </motion.section>
        )}
      </AnimatePresence>

      {movies.length > 0 && (
        <section style={{ width: "100%", maxWidth: 900, display: "flex", flexDirection: "column", gap: 14 }}>
          <p
            style={{
              color: "rgba(255,255,255,0.55)",
              fontSize: 14,
              fontWeight: 600,
              margin: 0,
            }}
          >
            Добавленные фильмы ({movies.length})
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: 16,
            }}
          >
            {movies.map((sm) => (
              <div key={sm.id} style={{ position: "relative", display: "flex", flexDirection: "column", gap: 8 }}>
                <button
                  onClick={() => handleRemoveMovie(sm.id)}
                  aria-label="Удалить фильм из сессии"
                  style={{
                    position: "absolute",
                    top: -8,
                    right: -8,
                    zIndex: 2,
                    width: 26,
                    height: 26,
                    borderRadius: "50%",
                    border: "none",
                    background: "#E82323",
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    boxShadow: "0 4px 10px rgba(0,0,0,0.3)",
                  }}
                >
                  <X size={12} strokeWidth={2.5} />
                </button>
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
                      sizes="200px"
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
                <p
                  style={{
                    color: "#fff",
                    fontSize: 12,
                    fontWeight: 700,
                    lineHeight: "16px",
                    margin: 0,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {sm.movie?.title}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
      
      <div
        data-scroll-ignore
        style={{
          position: "sticky",
          bottom: 16,
          width: "min(100%, 400px)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          marginTop: "auto",
        }}
      >
        {nextGame && movies.length >= (nextGame === "movieco" ? 2 : 1) && (
          <Button variant="primary" className="w-full" onClick={handleContinue}>
            <Check size={16} className="mr-2" />
            Продолжить
          </Button>
        )}
        <Button
          variant="secondary"
          className="w-full"
          onClick={() => router.push(`/session/${code}`)}
        >
          Назад в лобби
        </Button>
      </div>
    </div>
  );
}
