import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import i18n from "../lib/i18n"
import { api } from "../lib/api"

export type User = {
  id: number
  name: string
  email: string
  role: "owner" | "admin" | "agent"
  email_verified: boolean
}

export type Company = {
  id: number
  name: string
  plan: string
  onboarding_step: string | null
  onboarding_completed_at: string | null
  profile: Record<string, any> | null
  lead_capture_enabled: boolean
  lead_capture_consent_text: string
}

type AuthState = {
  user: User | null
  company: Company | null
  isAuthenticated: boolean
  isLoading: boolean
  language: string
  setAuth: (user: User, company: Company | null) => void
  setCompany: (company: Company) => void
  updateUser: (partial: Partial<User>) => void
  logout: () => void
  setLanguage: (lang: string) => void
  bootstrap: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      company: null,
      isAuthenticated: false,
      isLoading: true,
      language: "en",
      setAuth: (user, company) =>
        set({ user, company, isAuthenticated: true, isLoading: false }),
      setCompany: (company) => set({ company }),
      updateUser: (partial) =>
        set((state) => ({ user: state.user ? { ...state.user, ...partial } : null })),
      logout: () =>
        set({ user: null, company: null, isAuthenticated: false, isLoading: false }),
      setLanguage: (lang) => {
        i18n.changeLanguage(lang)
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr"
        document.documentElement.lang = lang
        set({ language: lang })
      },
      // Restore the session from HttpOnly cookies. The 401 interceptor in
      // lib/api.ts silently refreshes an expired access cookie.
      bootstrap: async () => {
        try {
          const { data: user } = await api.get<User>("/auth/me")
          let company: Company | null = null
          try {
            company = (await api.get<Company>("/company")).data
          } catch {
            company = null
          }
          set({ user, company, isAuthenticated: true, isLoading: false })
        } catch {
          set({ user: null, company: null, isAuthenticated: false, isLoading: false })
        }
      },
    }),
    {
      name: "teledesk-auth",
      storage: createJSONStorage(() => localStorage),
      // NOTE: no token is persisted. Sessions are cookie-based.
      partialize: (state) => ({ user: state.user, company: state.company, language: state.language }),
    },
  ),
)