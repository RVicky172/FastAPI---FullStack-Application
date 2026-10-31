/**
 * One shared axios instance for the whole app.
 *
 * Interceptors are axios's version of "middleware" on the client side:
 *
 *   component -> api.get() -> [REQUEST interceptor] -> network -> FastAPI
 *   component <- result    <- [RESPONSE interceptor] <- network <- FastAPI
 */
import axios from "axios";

export const TOKEN_KEY = "access_token";

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
  timeout: 10_000,
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// REQUEST interceptor: runs before every request leaves the browser.
// Attaches the JWT so we never have to add it manually in each call.
// ---------------------------------------------------------------------------
api.interceptors.request.use(
  (config) => {
    const token = tokenStorage.get();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    config.metadata = { startTime: performance.now() };
    return config;
  },
  (error) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// RESPONSE interceptor: runs on every response (success or error).
// ---------------------------------------------------------------------------
api.interceptors.response.use(
  (response) => {
    const ms = (performance.now() - response.config.metadata.startTime).toFixed(0);
    // X-Request-ID / X-Process-Time come from our FastAPI middleware.
    // We can only read them because CORS `expose_headers` allows it.
    console.log(
      `[api] ${response.config.method.toUpperCase()} ${response.config.url}`,
      `-> ${response.status} | round-trip ${ms}ms`,
      `| server ${response.headers["x-process-time"]}`,
      `| req-id ${response.headers["x-request-id"]}`
    );
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const isLoginCall = error.config?.url?.includes("/auth/login");

    // 401 = token missing/expired/invalid -> log the user out everywhere.
    if (status === 401 && !isLoginCall) {
      tokenStorage.clear();
      window.dispatchEvent(new Event("auth:logout")); // AuthContext listens
    }

    // Turn FastAPI's error formats into one readable message.
    error.message = getErrorMessage(error);
    return Promise.reject(error);
  }
);

/**
 * FastAPI errors come as:
 *   { detail: "Some message" }                       (HTTPException)
 *   { detail: [{ loc: [...], msg: "..." }, ...] }    (422 validation error)
 */
export function getErrorMessage(error) {
  if (!error.response) return "Cannot reach server. Is the backend running?";
  const detail = error.response.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join(", ");
  }
  return `Request failed (${error.response.status})`;
}

export default api;
