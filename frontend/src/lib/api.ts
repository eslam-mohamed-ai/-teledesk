import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios"
import { getCookie } from "./cookies"

const API_BASE = import.meta.env.VITE_API_BASE || "/api"

export const COOKIE_CSRF = "teledesk_csrf"

export function getCsrfToken(): string | null {
  return getCookie(COOKIE_CSRF)
}

export function createApi(): AxiosInstance {
  const api = axios.create({
    baseURL: API_BASE,
    withCredentials: true,
    headers: { "Content-Type": "application/json" },
  })

  // Cookie-based auth: the access token lives in an HttpOnly cookie. We only
  // mirror the double-submit CSRF token into a header.
  api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const csrf = getCsrfToken()
    if (csrf) config.headers["X-CSRF-Token"] = csrf
    return config
  })

  // Silent refresh: on 401 call POST /auth/refresh (rotating refresh cookie),
  // then replay the original request once. No tokens touch JavaScript storage.
  api.interceptors.response.use(
    (res) => res,
    async (err) => {
      const original = err.config
      const isRefreshCall = original?.url?.includes("/auth/refresh")
      // /auth/me is the session probe run on every page load. A 401 there
      // simply means "not signed in" and must not trigger a redirect loop.
      const isAuthProbe = original?.url?.includes("/auth/me")
      if (err.response?.status === 401 && !original?._retry && !isRefreshCall && !isAuthProbe) {
        original._retry = true
        try {
          await axios.post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
          return api(original)
        } catch {
          if (!window.location.pathname.startsWith("/auth/")) {
            window.location.href = "/auth/login"
          }
          return Promise.reject(err)
        }
      }
      return Promise.reject(err)
    },
  )

  return api
}

export const api = createApi()

export function errorMessage(error: unknown, fallback = "Something went wrong"): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
    return String((detail[0] as { msg: string }).msg)
  }
  return fallback
}

export type { AxiosInstance }