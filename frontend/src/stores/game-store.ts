import { create } from "zustand";
import type { TournamentRoomState } from "@/types";

interface GameState {
  gameType: "flappy" | "movieco" | null;
  tournamentState: TournamentRoomState | null;
  userKey: string | null;
  setGameType: (type: "flappy" | "movieco") => void;
  setTournamentState: (state: TournamentRoomState) => void;
  setUserKey: (key: string) => void;
  reset: () => void;
}

export const useGameStore = create<GameState>()((set) => ({
  gameType: null,
  tournamentState: null,
  userKey: null,
  setGameType: (type) => set({ gameType: type }),
  setTournamentState: (state) => set({ tournamentState: state }),
  setUserKey: (key) => set({ userKey: key }),
  reset: () =>
    set({ gameType: null, tournamentState: null, userKey: null }),
}));
