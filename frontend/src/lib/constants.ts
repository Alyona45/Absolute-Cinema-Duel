export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const normalizeWsBaseUrl = (value: string): string => {
  const normalized = trimTrailingSlash(value.trim());
  if (!normalized) return "";

  if (normalized.startsWith("ws://") || normalized.startsWith("wss://")) {
    return normalized;
  }

  if (normalized.startsWith("http://")) {
    return `ws://${normalized.slice("http://".length)}`;
  }

  if (normalized.startsWith("https://")) {
    return `wss://${normalized.slice("https://".length)}`;
  }

  return normalized;
};

export const getWsBaseUrl = (): string => {
  const explicit = normalizeWsBaseUrl(process.env.NEXT_PUBLIC_WS_URL || "");
  if (explicit) {
    if (typeof window !== "undefined") {
      try {
        const explicitUrl = new URL(explicit);
        const isExplicitLocalhost = ["localhost", "127.0.0.1", "::1"].includes(
          explicitUrl.hostname
        );
        const isPageLocalhost = ["localhost", "127.0.0.1", "::1"].includes(
          window.location.hostname
        );
        if (!isExplicitLocalhost || isPageLocalhost) {
          return explicit;
        }
      } catch {
        return explicit;
      }
    } else {
      return explicit;
    }
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}`;
  }

  return WS_URL;
};

export const GAME_TYPES = {
  FLAPPY: "flappy",
  MOVIECO: "movieco",
} as const;

export const SESSION_STATUS = {
  WAITING: "WAITING",
  PLAYING: "PLAYING",
  FINISHED: "FINISHED",
} as const;

export const TOURNAMENT_STATUS = {
  LOBBY: "LOBBY",
  RUNNING: "RUNNING",
  FINISHED: "FINISHED",
} as const;
