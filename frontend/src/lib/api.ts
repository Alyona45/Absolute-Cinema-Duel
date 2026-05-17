const DEV = process.env.NODE_ENV !== "production";

type AuthRefresher = () => Promise<string | null>;

class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private refresher: AuthRefresher | null = null;
  private refreshInflight: Promise<string | null> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.accessToken = token;
  }

  setAuthRefresher(refresher: AuthRefresher | null) {
    this.refresher = refresher;
  }

  private async runRefresh(): Promise<string | null> {
    if (!this.refresher) return null;
    if (this.refreshInflight) return this.refreshInflight;
    this.refreshInflight = this.refresher().finally(() => {
      this.refreshInflight = null;
    });
    return this.refreshInflight;
  }

  private formatRequestBodyForLog(body: RequestInit["body"]): unknown {
    if (!body) return undefined;

    if (typeof body === "string") {
      try {
        return JSON.parse(body);
      } catch {
        return body;
      }
    }

    if (body instanceof URLSearchParams) {
      return Object.fromEntries(body.entries());
    }

    if (body instanceof FormData) {
      const entries: Record<string, string> = {};
      for (const [key, value] of body.entries()) {
        entries[key] = typeof value === "string" ? value : `[File:${value.name}]`;
      }
      return entries;
    }

    return "[unserializable body]";
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    _retry = false,
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }

    if (!(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
      headers["Content-Type"] = "application/json";
    }

    const url = `${this.baseUrl}${path}`;
    if (DEV) {
      console.log(
        `[API] ${options.method || "GET"} ${url}`,
        this.formatRequestBodyForLog(options.body)
      );
    }

    const res = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    if (DEV) {
      console.log(`[API] ${options.method || "GET"} ${url} → ${res.status}`);
    }

    if (!res.ok) {
      if (
        res.status === 401 &&
        !_retry &&
        this.refresher &&
        !path.startsWith("/auth/refresh") &&
        !path.startsWith("/auth/login")
      ) {
        const newToken = await this.runRefresh();
        if (newToken) {
          return this.request<T>(path, options, true);
        }
      }

      const body = await res.json().catch(() => ({}));
      if (DEV) console.error(`[API] ERROR ${res.status}:`, body);
      throw new ApiError(res.status, body.detail || res.statusText);
    }

    if (res.status === 204) return undefined as T;
    const json = await res.json();
    if (DEV) {
      console.log(`[API] ${options.method || "GET"} ${url} response:`, json);
    }
    return json;
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  delete(path: string) {
    return this.request(path, { method: "DELETE" });
  }

  postForm<T>(path: string, formData: FormData) {
    return this.request<T>(path, {
      method: "POST",
      body: formData,
    });
  }

  postFormLogin<T>(path: string, username: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    return this.request<T>(path, {
      method: "POST",
      body: form,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const api = new ApiClient("/api");
