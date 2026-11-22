import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"
import i18n from "../lib/i18n"

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
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  setAuth: (user: User, company: Company, token: string) => void
  setCompany: (company: Company) => void
  updateUser: (partial: Partial<User>) => void
  logout: () => void
  setLanguage: (lang: string) => void
  language: string
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      company: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,
      language: "en",
      setAuth: (user, company, token) =>
        set({ user, company, token, isAuthenticated: true, isLoading: false }),
      setCompany: (company) => set({ company }),
      updateUser: (partial) =>
        set((state) => ({ user: state.user ? { ...state.user, ...partial } : null })),
      logout: () =>
        set({ user: null, company: null, token: null, isAuthenticated: false, isLoading: false }),
      setLanguage: (lang) => {
        i18n.changeLanguage(lang)
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr"
        document.documentElement.lang = lang
        set({ language: lang })
      },
    }),
    {
      name: "teledesk-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user, company: state.company, token: state.token, language: state.language }),
    },
  )
)
