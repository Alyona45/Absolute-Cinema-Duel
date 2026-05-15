"use client";

import { useEffect, useState } from "react";
import { useUserStore } from "@/stores/user-store";
import { api } from "@/lib/api";
import type { TokenResponse } from "@/types";

export function AuthHydrator() {
  const [hydrated, setHydrated] = useState(() =>
    typeof window !== "undefined"
      ? useUserStore.persist.hasHydrated()
      : false
  );

  useEffect(() => {
    if (hydrated) return;
    if (useUserStore.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsub = useUserStore.persist.onFinishHydration(() => {
      setHydrated(true);
    });
    return unsub;
  }, [hydrated]);

  const accessToken = useUserStore((s) => s.accessToken);
  const userId = useUserStore((s) => s.userId);
  const runtimeUserId = useUserStore((s) => s.runtimeUserId);
  const setRuntimeUserId = useUserStore((s) => s.setRuntimeUserId);

  useEffect(() => {
    if (!hydrated) return;
    api.setToken(accessToken);
  }, [hydrated, accessToken]);

  useEffect(() => {
    if (!hydrated) return;

    api.setAuthRefresher(async () => {
      const state = useUserStore.getState();
      const rt = state.refreshToken;
      if (!rt) return null;

      try {
        const res = await fetch("/api/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
          credentials: "include",
        });

        if (!res.ok) {
          state.logout();
          return null;
        }

        const tokens = (await res.json()) as TokenResponse;

        useUserStore.setState({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isGuest: false,
        });
        api.setToken(tokens.access_token);
        return tokens.access_token;
      } catch {
        return null;
      }
    });

    return () => {
      api.setAuthRefresher(null);
    };
  }, [hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    if (userId != null) {
      const expected = String(userId);
      if (runtimeUserId !== expected) {
        setRuntimeUserId(expected);
      }
    }
  }, [hydrated, userId, runtimeUserId, setRuntimeUserId]);

  return null;
}
