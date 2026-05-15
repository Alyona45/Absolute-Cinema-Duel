"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import Image from "next/image";
import { Search } from "lucide-react";
import type { MovieSearchResult } from "@/types";
import { useSessionStore } from "@/stores/session-store";
import { useToastStore } from "@/stores/toast-store";
import { motion } from "framer-motion";

export default function MovieSearchPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");
  const { addToast } = useToastStore();
  const { addMovie } = useSessionStore();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const search = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.get<MovieSearchResult[]>(
        `/movies/search?query=${encodeURIComponent(q.trim())}`
      );
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(debounceRef.current ?? undefined);
    debounceRef.current = setTimeout(() => search(val), 400);
  };

  const handleSelect = async (movie: MovieSearchResult) => {
    if (!sessionId) {
      addToast("Сессия не указана", "error");
      return;
    }
    try {
      await api.post(`/sessions/${sessionId}/movies`, {
        kinopoisk_id: movie.kinopoisk_id,
      });
      addToast(`"${movie.title}" добавлен`, "success");
    } catch {
      addToast("Не удалось добавить фильм", "error");
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100dvh-5rem)] px-6 py-6 gap-6">
      <div className="relative">
        <Search
          size={18}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500 z-10"
        />
        <input
          type="text"
          value={query}
          onChange={handleChange}
          placeholder="Поиск фильмов..."
          className="w-full pl-11 pr-4 py-3.5 rounded-2xl bg-white/5 text-white placeholder:text-neutral-500 outline-none focus:ring-2 focus:ring-red-600 transition-all"
          autoFocus
        />
      </div>

      {!searched && !loading && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-neutral-500 text-center">
            Начните вводить название фильма...
          </p>
        </div>
      )}

      {/* Загрузка */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex flex-col gap-2">
              <Skeleton className="w-full aspect-[2/3] rounded-2xl" />
              <Skeleton className="w-3/4 h-3 rounded" />
              <Skeleton className="w-1/2 h-3 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Сетка результатов */}
      {!loading && searched && results.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {results.map((movie, i) => (
            <motion.button
              key={movie.kinopoisk_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => handleSelect(movie)}
              className="flex flex-col gap-2 text-left hover:opacity-80 transition-opacity"
            >
              {movie.poster_url ? (
                <Image
                  src={movie.poster_url}
                  alt={movie.title}
                  width={120}
                  height={180}
                  className="w-full aspect-[2/3] object-cover rounded-2xl"
                />
              ) : (
                <div className="w-full aspect-[2/3] bg-neutral-700 rounded-2xl flex items-center justify-center">
                  <span className="text-2xl">🎬</span>
                </div>
              )}
              <p className="text-white text-xs font-bold line-clamp-2">
                {movie.title}
              </p>
              <p className="text-neutral-500 text-[10px]">
                {[movie.year, movie.director].filter(Boolean).join(" · ")}
              </p>
            </motion.button>
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-neutral-500 text-center">
            Ничего не найдено
          </p>
        </div>
      )}
    </div>
  );
}
