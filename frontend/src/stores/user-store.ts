import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface UserState {
  isGuest: boolean;
  userId: number | null;
  runtimeUserId: string | null;
  username: string | null;
  email: string | null;
  avatarUrl: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  guestName: string | null;
  setAuth: (data: {
    userId: number;
    username: string;
    email: string;
    avatarUrl: string | null;
    accessToken: string;
    refreshToken: string;
  }) => void;
  setGuest: (name: string, runtimeUserId?: string | null) => void;
  setRuntimeUserId: (runtimeUserId: string | null) => void;
  updateProfile: (data: {
    username?: string;
    email?: string;
    avatarUrl?: string | null;
  }) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      isGuest: true,
      userId: null,
      runtimeUserId: null,
      username: null,
      email: null,
      avatarUrl: null,
      accessToken: null,
      refreshToken: null,
      guestName: null,
      setAuth: (data) =>
        set({
          isGuest: false,
          userId: data.userId,
          runtimeUserId: String(data.userId),
          username: data.username,
          email: data.email,
          avatarUrl: data.avatarUrl,
          accessToken: data.accessToken,
          refreshToken: data.refreshToken,
        }),
      setGuest: (name, runtimeUserId = null) =>
        set({
          isGuest: true,
          guestName: name,
          userId: null,
          runtimeUserId,
          accessToken: null,
          refreshToken: null,
        }),
      setRuntimeUserId: (runtimeUserId) => set({ runtimeUserId }),
      updateProfile: (data) =>
        set((state) => ({
          username: data.username ?? state.username,
          email: data.email ?? state.email,
          avatarUrl: data.avatarUrl !== undefined ? data.avatarUrl : state.avatarUrl,
        })),
      logout: () =>
        set({
          isGuest: true,
          userId: null,
          runtimeUserId: null,
          username: null,
          email: null,
          avatarUrl: null,
          accessToken: null,
          refreshToken: null,
        }),
    }),
    {
      name: "user-store",
      version: 1,
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : (undefined as unknown as Storage)
      ),
      migrate: (persistedState) => persistedState as Partial<UserState>,
      partialize: (state) => ({
        isGuest: state.isGuest,
        userId: state.userId,
        runtimeUserId: state.runtimeUserId,
        username: state.username,
        email: state.email,
        avatarUrl: state.avatarUrl,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        guestName: state.guestName,
      }),
    }
  )
);
