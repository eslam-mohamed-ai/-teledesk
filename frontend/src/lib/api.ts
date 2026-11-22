import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios"
import { getCookie, setCookie, removeCookie } from "./cookies"

const API_BASE = import.meta.env.VITE_API_BASE || "/api"

export const COOKIE_ACCESS = "teledesk_session"
export const COOKIE_REFRESH = "teledesk_refresh"
export const COOKIE_CSRF = "teledesk_csrf"

let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

export function createApi(): AxiosInstance {
  const api = axios.create({
    baseURL: API_BASE,
    withCredentials: true,
    headers: {
      "Content-Type": "application/json",
    },
  })

  api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const csrf = getCookie(COOKIE_CSRF)
    if (csrf) {
      config.headers["X-CSRF-Token"] = csrf
    }
    return config
  })

  api.interceptors.response.use(
    (res) => res,
    async (err) => {
      const original = err.config
      if (err.response?.status === 401 && !original._retry) {
        original._retry = true
        if (!isRefreshing) {
          isRefreshing = true
          try {
            const { data } = await axios.post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
            const access = data.access_token
            if (access) {
              setCookie(COOKIE_ACCESS, access, 900)
              onRefreshed(access)
            }
            return api(original)
          } catch {
            removeCookie(COOKIE_ACCESS)
            removeCookie(COOKIE_REFRESH)
            removeCookie(COOKIE_CSRF)
            window.location.href = "/auth/login"
            return Promise.reject(err)
          } finally {
            isRefreshing = false
          }
        }
        return new Promise((resolve) => {
          addRefreshSubscriber((token) => {
            original.headers["Authorization"] = `Bearer ${token}`
            resolve(api(original))
          })
        })
      }
      return Promise.reject(err)
    },
  )

  return api
}

export const api = createApi()

export type { AxiosInstance }
