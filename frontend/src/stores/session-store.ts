import { create } from "zustand";
import type { GameSession, SessionParticipant, SessionMovie } from "@/types";

interface SessionState {
  session: GameSession | null;
  participants: SessionParticipant[];
  movies: SessionMovie[];
  setSession: (session: GameSession) => void;
  setParticipants: (participants: SessionParticipant[]) => void;
  addParticipant: (p: SessionParticipant) => void;
  setMovies: (movies: SessionMovie[]) => void;
  addMovie: (movie: SessionMovie) => void;
  removeMovie: (movieId: number) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>()((set) => ({
  session: null,
  participants: [],
  movies: [],
  setSession: (session) => set({ session }),
  setParticipants: (participants) => set({ participants }),
  addParticipant: (p) =>
    set((s) => ({
      participants: s.participants.some((x) => x.id === p.id)
        ? s.participants
        : [...s.participants, p],
    })),
  setMovies: (movies) => set({ movies }),
  addMovie: (movie) => set((s) => ({ movies: [...s.movies, movie] })),
  removeMovie: (movieId) =>
    set((s) => ({ movies: s.movies.filter((m) => m.id !== movieId) })),
  reset: () => set({ session: null, participants: [], movies: [] }),
}));
