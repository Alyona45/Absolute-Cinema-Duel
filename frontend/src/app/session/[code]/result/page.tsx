"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast-store";
import { useUserStore } from "@/stores/user-store";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import type { GameSession, Movie, User } from "@/types";

const POSTER_ASPECT = 625 / 424;

function formatRating(m: Movie): string | null {
  const v = m.rating_kinopoisk ?? m.rating;
  if (v == null) return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return n.toFixed(1);
}

function genreLabels(m: Movie): string[] {
  if (!m.genres) return [];
  return m.genres.map((g) => ("genre" in g ? g.genre.name : g.name));
}

function PosterFace({ movie }: { movie: Movie }) {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        borderRadius: 30,
        overflow: "hidden",
        background: "#D9D9D9",
      }}
    >
      {movie.poster_url ? (
        <Image
          src={movie.poster_url}
          alt={movie.title}
          fill
          sizes="(max-width: 640px) 80vw, 424px"
          className="object-cover"
          priority
        />
      ) : (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontSize: 18,
            fontWeight: 700,
            padding: 24,
            textAlign: "center",
          }}
        >
          {movie.title}
        </div>
      )}
    </div>
  );
}

function DetailsFace({ movie }: { movie: Movie }) {
  const rating = formatRating(movie);
  const genres = genreLabels(movie);

  const summary = movie.short_description || movie.description || "";

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        borderRadius: 30,
        background: "#F4F4F4",
        padding: "32px 22px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 18,
        boxShadow: "3px 2px 4px #272727",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 18, minHeight: 0 }}>
        <h2
          style={{
            color: "#000",
            fontSize: 22,
            fontWeight: 700,
            lineHeight: "28px",
            margin: 0,
          }}
        >
          {movie.title}
          {movie.year && (
            <>
              <br />
              <span style={{ fontWeight: 700 }}>
                ({movie.year}
                {movie.director ? `, ${movie.director}` : ""})
              </span>
            </>
          )}
        </h2>

        {summary && (
          <p
            style={{
              color: "#000",
              fontSize: 15,
              fontWeight: 500,
              lineHeight: "22px",
              margin: 0,
              display: "-webkit-box",
              WebkitLineClamp: 8,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {summary}
          </p>
        )}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        {rating && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "#B90000",
              color: "#fff",
              padding: "6px 14px",
              borderRadius: 30,
              fontSize: 18,
              fontWeight: 800,
              lineHeight: 1,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="#fff">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.27 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z" />
            </svg>
            <span>{rating}</span>
          </div>
        )}
        {genres.length > 0 && (
          <span
            style={{
              color: "#000",
              fontSize: 16,
              fontWeight: 700,
              lineHeight: "22px",
            }}
          >
            {genres.slice(0, 3).join(", ")}
          </span>
        )}
      </div>
    </div>
  );
}

export default function ResultPage() {
  const params = useParams();
  const router = useRouter();
  const code = params.code as string;
  const { addToast } = useToastStore();
  const { isGuest } = useUserStore();

  const [winnerMovie, setWinnerMovie] = useState<Movie | null>(null);
  const [winnerUser, setWinnerUser] = useState<
    { username: string; avatar_url: string | null } | null
  >(null);
  const [loading, setLoading] = useState(true);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const sess = await api.get<GameSession>(`/sessions/by-code/${code}`);
        if (!sess) {
          addToast("Сессия не найдена", "error");
          router.push("/");
          return;
        }

        const embedded = sess.winner_session_movie?.movie ?? null;
        if (embedded) {
          setWinnerMovie(embedded);
        } else if (sess.winner_movie_id) {
          setWinnerMovie(await api.get<Movie>(`/movies/${sess.winner_movie_id}`));
        }

        if (sess.winner_user_id) {
          try {
            const user = await api.get<User>(`/users/${sess.winner_user_id}`);
            setWinnerUser({
              username: user.username,
              avatar_url: user.avatar_url,
            });
          } catch {
            setWinnerUser({ username: "Победитель", avatar_url: null });
          }
        } else {
          const p = (sess.winner_session_movie as { participant?: { display_name: string } } | null | undefined)
            ?.participant;
          if (p?.display_name) {
            setWinnerUser({ username: p.display_name, avatar_url: null });
          }
        }
      } catch (err) {
        console.error("Result fetch error:", err);
        addToast("Ошибка загрузки результатов", "error");
      } finally {
        setLoading(false);
      }
    };
    fetchResult();
  }, [code, addToast, router]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "calc(100dvh - 5.5rem)",
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

  if (!winnerMovie) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "calc(100dvh - 5.5rem)",
          gap: 24,
          padding: 24,
        }}
      >
        <h2 style={{ color: "#fff", fontSize: 20, fontWeight: 700 }}>
          Результаты ещё не определены
        </h2>
        <Button variant="secondary" onClick={() => router.push(`/session/${code}`)}>
          Вернуться в лобби
        </Button>
      </div>
    );
  }

  return (
    <div
      style={{
        height: "calc(100dvh - 5.5rem)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px clamp(16px, 4vw, 40px) 16px",
        gap: 14,
        overflow: "hidden",
      }}
    >
      <motion.button
        type="button"
        onClick={() => setFlipped((v) => !v)}
        aria-label={flipped ? "Показать постер" : "Показать описание"}
        initial={{ opacity: 0, scale: 0.95, y: 24 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 160, damping: 22 }}
        style={{
          position: "relative",
          width: `min(100%, 340px, calc((100dvh - 5.5rem - 180px) / ${POSTER_ASPECT}))`,
          aspectRatio: `1 / ${POSTER_ASPECT}`,
          padding: 0,
          border: "none",
          background: "transparent",
          cursor: "pointer",
          borderRadius: 30,
          boxShadow: "6px 6px 8px rgba(0,0,0,0.35)",
          flexShrink: 0,
        }}
      >
        <AnimatePresence initial={false} mode="wait">
          {flipped ? (
            <motion.div
              key="details"
              initial={{ opacity: 0, rotateY: -90 }}
              animate={{ opacity: 1, rotateY: 0 }}
              exit={{ opacity: 0, rotateY: 90 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              style={{ position: "absolute", inset: 0, transformStyle: "preserve-3d" }}
            >
              <DetailsFace movie={winnerMovie} />
            </motion.div>
          ) : (
            <motion.div
              key="poster"
              initial={{ opacity: 0, rotateY: -90 }}
              animate={{ opacity: 1, rotateY: 0 }}
              exit={{ opacity: 0, rotateY: 90 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              style={{ position: "absolute", inset: 0 }}
            >
              <PosterFace movie={winnerMovie} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      <p
        style={{
          color: "rgba(255,255,255,0.45)",
          fontSize: 13,
          fontWeight: 500,
          margin: 0,
        }}
      >
        {flipped ? "Нажмите, чтобы увидеть постер" : "Нажмите на карточку, чтобы увидеть описание"}
      </p>

      {winnerUser && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 220, damping: 22 }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 20,
          }}
        >
          <Avatar
            name={winnerUser.username}
            src={winnerUser.avatar_url}
            size="sm"
            borderColor="red"
          />
          <span
            style={{
              color: "#fff",
              fontSize: 20,
              fontWeight: 800,
              lineHeight: "20px",
            }}
          >
            {winnerUser.username}
          </span>
        </motion.div>
      )}

      <div style={{ width: "min(100%, 330px)" }}>
        <Button
          variant="primary"
          className="w-full"
          onClick={() => router.push(isGuest ? "/" : "/profile")}
        >
          Готово
        </Button>
      </div>
    </div>
  );
}
