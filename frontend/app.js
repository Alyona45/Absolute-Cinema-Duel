const STORAGE_KEY = "acd_demo_state_v1";

const state = {
  apiBase: window.location.origin,
  accessToken: "",
  refreshToken: "",
  roomId: "",
  roomUserId: "",
};

let ws = null;

const els = {
  apiBase: document.getElementById("apiBase"),
  saveConfigBtn: document.getElementById("saveConfigBtn"),
  clearStateBtn: document.getElementById("clearStateBtn"),
  stateBadges: document.getElementById("stateBadges"),

  registerForm: document.getElementById("registerForm"),
  loginForm: document.getElementById("loginForm"),
  refreshBtn: document.getElementById("refreshBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  accessToken: document.getElementById("accessToken"),
  refreshToken: document.getElementById("refreshToken"),
  saveTokensBtn: document.getElementById("saveTokensBtn"),

  meBtn: document.getElementById("meBtn"),
  patchMeForm: document.getElementById("patchMeForm"),
  changePasswordForm: document.getElementById("changePasswordForm"),
  avatarForm: document.getElementById("avatarForm"),
  adminUserId: document.getElementById("adminUserId"),
  adminGetUserBtn: document.getElementById("adminGetUserBtn"),
  adminDeleteUserBtn: document.getElementById("adminDeleteUserBtn"),

  createMovieForm: document.getElementById("createMovieForm"),
  movieIdInput: document.getElementById("movieIdInput"),
  getMovieByIdBtn: document.getElementById("getMovieByIdBtn"),
  kinopoiskIdInput: document.getElementById("kinopoiskIdInput"),
  getMovieByKpBtn: document.getElementById("getMovieByKpBtn"),
  getGenresBtn: document.getElementById("getGenresBtn"),
  replaceGenresForm: document.getElementById("replaceGenresForm"),
  movieGenresIdInput: document.getElementById("movieGenresIdInput"),
  getMovieGenresBtn: document.getElementById("getMovieGenresBtn"),

  createSessionBtn: document.getElementById("createSessionBtn"),
  mySessionsBtn: document.getElementById("mySessionsBtn"),
  sessionIdInput: document.getElementById("sessionIdInput"),
  getSessionBtn: document.getElementById("getSessionBtn"),
  joinSessionBtn: document.getElementById("joinSessionBtn"),
  leaveSessionBtn: document.getElementById("leaveSessionBtn"),
  participantsBtn: document.getElementById("participantsBtn"),
  proposeMovieForm: document.getElementById("proposeMovieForm"),
  sessionMovieIdInput: document.getElementById("sessionMovieIdInput"),
  deleteSessionMovieBtn: document.getElementById("deleteSessionMovieBtn"),
  sessionMoviesBtn: document.getElementById("sessionMoviesBtn"),
  winnerForm: document.getElementById("winnerForm"),

  roomUseAuth: document.getElementById("roomUseAuth"),
  createRoomForm: document.getElementById("createRoomForm"),
  joinRoomForm: document.getElementById("joinRoomForm"),
  roomStateForm: document.getElementById("roomStateForm"),
  startRoomForm: document.getElementById("startRoomForm"),

  wsUseToken: document.getElementById("wsUseToken"),
  wsConnectForm: document.getElementById("wsConnectForm"),
  wsDisconnectBtn: document.getElementById("wsDisconnectBtn"),
  wsPingBtn: document.getElementById("wsPingBtn"),

  clearLogBtn: document.getElementById("clearLogBtn"),
  logOutput: document.getElementById("logOutput"),
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw);
    state.apiBase = parsed.apiBase || state.apiBase;
    state.accessToken = parsed.accessToken || "";
    state.refreshToken = parsed.refreshToken || "";
    state.roomId = parsed.roomId || "";
    state.roomUserId = parsed.roomUserId || "";
  } catch {
    log("WARN", { message: "Не удалось прочитать локальное состояние" });
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function renderState() {
  els.apiBase.value = state.apiBase;
  els.accessToken.value = state.accessToken;
  els.refreshToken.value = state.refreshToken;

  const badges = [];
  badges.push(`<span class="badge">API: ${escapeHtml(state.apiBase)}</span>`);
  badges.push(`<span class="badge">Access: ${state.accessToken ? "есть" : "нет"}</span>`);
  badges.push(`<span class="badge">Refresh: ${state.refreshToken ? "есть" : "нет"}</span>`);
  if (state.roomId) {
    badges.push(`<span class="badge">Room: ${escapeHtml(state.roomId)}</span>`);
  }
  if (state.roomUserId) {
    badges.push(`<span class="badge">User in room: ${escapeHtml(state.roomUserId)}</span>`);
  }
  els.stateBadges.innerHTML = badges.join("");
}

function log(label, payload, isError = false) {
  const now = new Date().toISOString();
  const mark = isError ? "ERROR" : "INFO";
  const line = `[${now}] [${mark}] ${label}\n${JSON.stringify(payload, null, 2)}\n\n`;
  els.logOutput.textContent = line + els.logOutput.textContent;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeBase(base) {
  return base.trim().replace(/\/$/, "");
}

function wsBaseFromApi(apiBase) {
  const url = new URL(apiBase);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}`;
}

function getRequiredValue(input, name) {
  const value = (input.value || "").trim();
  if (!value) {
    throw new Error(`Поле ${name} обязательно`);
  }
  return value;
}

async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (response.status === 204) {
    return null;
  }
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

async function apiRequest(method, path, options = {}) {
  const {
    body,
    auth = true,
    contentType = "application/json",
    extraHeaders = {},
  } = options;

  const headers = { ...extraHeaders };
  if (auth && state.accessToken) {
    headers.Authorization = `Bearer ${state.accessToken}`;
  }

  let payload = body;
  if (body != null && !(body instanceof FormData) && contentType) {
    headers["Content-Type"] = contentType;
    if (contentType === "application/json") {
      payload = JSON.stringify(body);
    }
  }

  const url = `${normalizeBase(state.apiBase)}${path}`;
  const response = await fetch(url, {
    method,
    headers,
    body: payload,
  });

  const data = await readResponse(response);
  if (!response.ok) {
    throw {
      status: response.status,
      data,
      method,
      path,
    };
  }

  return { status: response.status, data };
}

function setTokens(accessToken, refreshToken) {
  state.accessToken = accessToken || "";
  state.refreshToken = refreshToken || "";
  saveState();
  renderState();
}

function safeError(error) {
  if (error instanceof Error) {
    return { message: error.message };
  }
  return error;
}

function withGuard(handler) {
  return async (event) => {
    event.preventDefault();
    try {
      await handler(event);
    } catch (error) {
      log("Request failed", safeError(error), true);
    }
  };
}

function buildCleanObject(input) {
  const object = {};
  Object.entries(input).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined) {
      return;
    }
    object[key] = value;
  });
  return object;
}

function bindEvents() {
  els.saveConfigBtn.addEventListener("click", () => {
    state.apiBase = normalizeBase(els.apiBase.value || window.location.origin);
    saveState();
    renderState();
    log("Config saved", { apiBase: state.apiBase });
  });

  els.clearStateBtn.addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    setTokens("", "");
    state.apiBase = window.location.origin;
    state.roomId = "";
    state.roomUserId = "";
    saveState();
    renderState();
    log("State cleared", { ok: true });
  });

  els.saveTokensBtn.addEventListener("click", () => {
    setTokens(els.accessToken.value.trim(), els.refreshToken.value.trim());
    log("Tokens updated manually", { ok: true });
  });

  els.registerForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const body = {
      email: String(form.get("email") || "").trim(),
      username: String(form.get("username") || "").trim(),
      password: String(form.get("password") || ""),
    };
    const result = await apiRequest("POST", "/auth/register", { body, auth: false });
    log("POST /auth/register", result);
  }));

  els.loginForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const params = new URLSearchParams();
    params.set("username", String(form.get("username") || "").trim());
    params.set("password", String(form.get("password") || ""));

    const result = await apiRequest("POST", "/auth/login", {
      body: params,
      auth: false,
      contentType: "application/x-www-form-urlencoded",
    });

    if (result.data && typeof result.data === "object") {
      setTokens(result.data.access_token, result.data.refresh_token);
    }

    log("POST /auth/login", result);
  }));

  els.refreshBtn.addEventListener("click", withGuard(async () => {
    const result = await apiRequest("POST", "/auth/refresh", {
      auth: false,
      body: { refresh_token: state.refreshToken || els.refreshToken.value.trim() },
    });

    if (result.data && typeof result.data === "object") {
      setTokens(result.data.access_token, result.data.refresh_token);
    }

    log("POST /auth/refresh", result);
  }));

  els.logoutBtn.addEventListener("click", withGuard(async () => {
    const result = await apiRequest("POST", "/auth/logout", {
      auth: false,
      body: { refresh_token: state.refreshToken || els.refreshToken.value.trim() },
    });
    setTokens("", "");
    log("POST /auth/logout", result);
  }));

  els.meBtn.addEventListener("click", withGuard(async () => {
    const result = await apiRequest("GET", "/users/me");
    log("GET /users/me", result);
  }));

  els.patchMeForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const body = buildCleanObject({
      username: String(form.get("username") || "").trim(),
      email: String(form.get("email") || "").trim(),
    });
    const result = await apiRequest("PATCH", "/users/me", { body });
    log("PATCH /users/me", result);
  }));

  els.changePasswordForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const body = {
      current_password: String(form.get("current_password") || ""),
      new_password: String(form.get("new_password") || ""),
    };
    const result = await apiRequest("POST", "/users/change-password", { body });
    log("POST /users/change-password", result);
  }));

  els.avatarForm.addEventListener("submit", withGuard(async (event) => {
    const formData = new FormData(event.currentTarget);
    const file = formData.get("file");
    if (!(file instanceof File)) {
      throw new Error("Нужно выбрать файл");
    }

    const upload = new FormData();
    upload.set("file", file);

    const result = await apiRequest("POST", "/users/me/avatar", {
      body: upload,
      contentType: "",
    });
    log("POST /users/me/avatar", result);
  }));

  els.adminGetUserBtn.addEventListener("click", withGuard(async () => {
    const userId = getRequiredValue(els.adminUserId, "admin user_id");
    const result = await apiRequest("GET", `/users/${encodeURIComponent(userId)}`);
    log("GET /users/{id}", result);
  }));

  els.adminDeleteUserBtn.addEventListener("click", withGuard(async () => {
    const userId = getRequiredValue(els.adminUserId, "admin user_id");
    const result = await apiRequest("DELETE", `/users/${encodeURIComponent(userId)}`);
    log("DELETE /users/{id}", result);
  }));

  els.createMovieForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const body = buildCleanObject({
      kinopoisk_id: Number(form.get("kinopoisk_id")),
      title: String(form.get("title") || "").trim(),
      short_description: String(form.get("short_description") || "").trim(),
      description: String(form.get("description") || "").trim(),
      poster_url: String(form.get("poster_url") || "").trim(),
      year: form.get("year") ? Number(form.get("year")) : "",
      runtime: form.get("runtime") ? Number(form.get("runtime")) : "",
      rating: form.get("rating") ? Number(form.get("rating")) : "",
    });
    const result = await apiRequest("POST", "/movies/", { body });
    log("POST /movies/", result);
  }));

  els.getMovieByIdBtn.addEventListener("click", withGuard(async () => {
    const movieId = getRequiredValue(els.movieIdInput, "movie_id");
    const result = await apiRequest("GET", `/movies/${encodeURIComponent(movieId)}`, { auth: false });
    log("GET /movies/{movie_id}", result);
  }));

  els.getMovieByKpBtn.addEventListener("click", withGuard(async () => {
    const kpId = getRequiredValue(els.kinopoiskIdInput, "kinopoisk_id");
    const result = await apiRequest("GET", `/movies/kinopoisk/${encodeURIComponent(kpId)}`, { auth: false });
    log("GET /movies/kinopoisk/{id}", result);
  }));

  els.getGenresBtn.addEventListener("click", withGuard(async () => {
    const result = await apiRequest("GET", "/movies/genres/all", { auth: false });
    log("GET /movies/genres/all", result);
  }));

  els.replaceGenresForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const movieId = String(form.get("movie_id") || "").trim();
    const genresRaw = String(form.get("genres") || "").trim();
    const genres = genresRaw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    const result = await apiRequest("PUT", `/movies/${encodeURIComponent(movieId)}/genres`, {
      body: genres,
    });
    log("PUT /movies/{movie_id}/genres", result);
  }));

  els.getMovieGenresBtn.addEventListener("click", withGuard(async () => {
    const movieId = getRequiredValue(els.movieGenresIdInput, "movie_id");
    const result = await apiRequest("GET", `/movies/${encodeURIComponent(movieId)}/genres`, { auth: false });
    log("GET /movies/{movie_id}/genres", result);
  }));

  els.createSessionBtn.addEventListener("click", withGuard(async () => {
    const result = await apiRequest("POST", "/sessions/");
    log("POST /sessions/", result);
  }));

  els.mySessionsBtn.addEventListener("click", withGuard(async () => {
    const result = await apiRequest("GET", "/sessions/my/list");
    log("GET /sessions/my/list", result);
  }));

  els.getSessionBtn.addEventListener("click", withGuard(async () => {
    const sessionId = getRequiredValue(els.sessionIdInput, "session_id");
    const result = await apiRequest("GET", `/sessions/${encodeURIComponent(sessionId)}`);
    log("GET /sessions/{session_id}", result);
  }));

  els.joinSessionBtn.addEventListener("click", withGuard(async () => {
    const sessionId = getRequiredValue(els.sessionIdInput, "session_id");
    const result = await apiRequest("POST", `/sessions/${encodeURIComponent(sessionId)}/participants`);
    log("POST /sessions/{id}/participants", result);
  }));

  els.leaveSessionBtn.addEventListener("click", withGuard(async () => {
    const sessionId = getRequiredValue(els.sessionIdInput, "session_id");
    const result = await apiRequest("DELETE", `/sessions/${encodeURIComponent(sessionId)}/participants`);
    log("DELETE /sessions/{id}/participants", result);
  }));

  els.participantsBtn.addEventListener("click", withGuard(async () => {
    const sessionId = getRequiredValue(els.sessionIdInput, "session_id");
    const result = await apiRequest("GET", `/sessions/${encodeURIComponent(sessionId)}/participants`);
    log("GET /sessions/{id}/participants", result);
  }));

  els.proposeMovieForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const sessionId = String(form.get("session_id") || "").trim();
    const movieId = String(form.get("movie_id") || "").trim();
    const result = await apiRequest(
      "POST",
      `/sessions/${encodeURIComponent(sessionId)}/movies?movie_id=${encodeURIComponent(movieId)}`,
    );
    log("POST /sessions/{id}/movies?movie_id=", result);
  }));

  els.deleteSessionMovieBtn.addEventListener("click", withGuard(async () => {
    const sessionId = getRequiredValue(els.sessionIdInput, "session_id");
    const sessionMovieId = getRequiredValue(els.sessionMovieIdInput, "session_movie_id");
    const result = await apiRequest(
      "DELETE",
      `/sessions/${encodeURIComponent(sessionId)}/movies/${encodeURIComponent(sessionMovieId)}`,
    );
    log("DELETE /sessions/{id}/movies/{session_movie_id}", result);
  }));

  els.sessionMoviesBtn.addEventListener("click", withGuard(async () => {
    const sessionId = getRequiredValue(els.sessionIdInput, "session_id");
    const result = await apiRequest("GET", `/sessions/${encodeURIComponent(sessionId)}/movies`);
    log("GET /sessions/{id}/movies", result);
  }));

  els.winnerForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const sessionId = String(form.get("session_id") || "").trim();
    const winnerSessionMovieId = String(form.get("winner_session_movie_id") || "").trim();

    const result = await apiRequest(
      "POST",
      `/sessions/${encodeURIComponent(sessionId)}/winner?winner_session_movie_id=${encodeURIComponent(winnerSessionMovieId)}`,
    );

    log("POST /sessions/{id}/winner", result);
  }));

  els.createRoomForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") || "").trim();
    const useAuth = Boolean(els.roomUseAuth.checked);

    const body = username ? { username } : null;
    const result = await apiRequest("POST", "/rooms", {
      body,
      auth: useAuth,
    });

    if (result.data && typeof result.data === "object") {
      state.roomId = result.data.room_id || state.roomId;
      state.roomUserId = result.data.user_id || state.roomUserId;
      saveState();
      renderState();
    }

    log("POST /rooms", result);
  }));

  els.joinRoomForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const roomId = String(form.get("room_id") || "").trim();
    const username = String(form.get("username") || "").trim();
    const body = username ? { username } : null;

    const result = await apiRequest("POST", `/rooms/${encodeURIComponent(roomId)}/join`, {
      body,
      auth: Boolean(els.roomUseAuth.checked),
    });

    if (result.data && typeof result.data === "object") {
      state.roomId = roomId;
      state.roomUserId = result.data.user_id || state.roomUserId;
      saveState();
      renderState();
    }

    log("POST /rooms/{room_id}/join", result);
  }));

  els.roomStateForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const roomId = String(form.get("room_id") || "").trim();
    const result = await apiRequest("GET", `/rooms/${encodeURIComponent(roomId)}`, { auth: false });
    log("GET /rooms/{room_id}", result);
  }));

  els.startRoomForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const roomId = String(form.get("room_id") || "").trim();
    const userId = String(form.get("user_id") || "").trim();
    const suffix = userId ? `?user_id=${encodeURIComponent(userId)}` : "";

    const result = await apiRequest("POST", `/rooms/${encodeURIComponent(roomId)}/start${suffix}`, {
      auth: Boolean(els.roomUseAuth.checked),
      body: null,
    });
    log("POST /rooms/{room_id}/start", result);
  }));

  els.wsConnectForm.addEventListener("submit", withGuard(async (event) => {
    const form = new FormData(event.currentTarget);
    const roomId = String(form.get("room_id") || "").trim();
    const userId = String(form.get("user_id") || "").trim();

    if (ws && ws.readyState <= 1) {
      ws.close(1000, "Reconnect");
      ws = null;
    }

    const wsBase = wsBaseFromApi(normalizeBase(state.apiBase));
    const useToken = Boolean(els.wsUseToken.checked);
    const tokenQuery = useToken && state.accessToken
      ? `?token=${encodeURIComponent(state.accessToken)}`
      : "";

    const url = `${wsBase}/ws/${encodeURIComponent(roomId)}/${encodeURIComponent(userId)}${tokenQuery}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
      log("WS open", { url });
      state.roomId = roomId;
      state.roomUserId = userId;
      saveState();
      renderState();
    };

    ws.onmessage = (messageEvent) => {
      let payload = messageEvent.data;
      try {
        payload = JSON.parse(messageEvent.data);
      } catch {
        // Если не JSON, пишем исходный текст.
      }
      log("WS message", payload);
    };

    ws.onerror = () => {
      log("WS error", { message: "Проверьте room_id/user_id/token" }, true);
    };

    ws.onclose = (eventClose) => {
      log("WS close", {
        code: eventClose.code,
        reason: eventClose.reason,
        wasClean: eventClose.wasClean,
      });
      ws = null;
    };
  }));

  els.wsDisconnectBtn.addEventListener("click", () => {
    if (!ws) {
      log("WS disconnect", { message: "Соединение не активно" });
      return;
    }
    ws.close(1000, "Closed by UI");
  });

  els.wsPingBtn.addEventListener("click", () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      log("WS ping", { message: "Соединение не установлено" }, true);
      return;
    }
    ws.send(JSON.stringify({ type: "PING" }));
    log("WS ping", { sent: { type: "PING" } });
  });

  els.clearLogBtn.addEventListener("click", () => {
    els.logOutput.textContent = "";
  });
}

function bootstrap() {
  loadState();
  state.apiBase = normalizeBase(state.apiBase || window.location.origin);
  renderState();
  bindEvents();
  log("Demo UI ready", {
    apiBase: state.apiBase,
    hint: "Начните с регистрации или логина",
  });
}

bootstrap();
