import { create } from "zustand"

export type Theme = "light" | "dark"

const STORAGE_KEY = "teledesk-theme"

function initialTheme(): Theme {
  if (typeof window === "undefined") return "light"
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === "light" || stored === "dark") return stored
  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ? "dark" : "light"
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return
  document.documentElement.classList.toggle("dark", theme === "dark")
  document.documentElement.style.colorScheme = theme
}

export const useThemeStore = create<{
  theme: Theme
  setTheme: (theme: Theme) => void
  toggle: () => void
}>((set, get) => ({
  theme: initialTheme(),
  setTheme: (theme) => {
    applyTheme(theme)
    window.localStorage.setItem(STORAGE_KEY, theme)
    set({ theme })
  },
  toggle: () => get().setTheme(get().theme === "dark" ? "light" : "dark"),
}))

// Apply the stored theme as early as possible.
applyTheme(useThemeStore.getState().theme)