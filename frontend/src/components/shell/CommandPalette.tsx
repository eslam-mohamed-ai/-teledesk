import * as React from "react"
import { useNavigate } from "react-router-dom"
import {
  Search,
  Mail,
  Users,
  Zap,
  Bot,
  FileText,
  BarChart2,
  Settings,
  Moon,
  Sun,
  LogOut,
  RefreshCw,
  Rocket,
} from "lucide-react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { useThemeStore } from "@/store/themeStore"
import { useAuthStore } from "@/store/authStore"
import { cn } from "@/lib/utils"

type Action = {
  id: string
  label: string
  hint?: string
  icon: React.ElementType
  run: () => void
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: Props) {
  const navigate = useNavigate()
  const toggleTheme = useThemeStore((state) => state.toggle)
  const theme = useThemeStore((state) => state.theme)
  const logout = useAuthStore((state) => state.logout)
  const [query, setQuery] = React.useState("")
  const [active, setActive] = React.useState(0)

  React.useEffect(() => {
    if (open) {
      setQuery("")
      setActive(0)
    }
  }, [open])

  const actions = React.useMemo<Action[]>(() => {
    const go = (path: string) => () => {
      navigate(path)
      onOpenChange(false)
    }
    return [
      { id: "inbox", label: "Go to Inbox", icon: Mail, run: go("/inbox") },
      { id: "contacts", label: "Go to Contacts", icon: Users, run: go("/contacts") },
      { id: "channels", label: "Go to Channels", icon: Zap, run: go("/channels") },
      { id: "ai", label: "Go to AI Agent", icon: Bot, run: go("/ai") },
      { id: "knowledge", label: "Go to Knowledge", icon: FileText, run: go("/knowledge") },
      { id: "analytics", label: "Go to Analytics", icon: BarChart2, run: go("/analytics") },
      { id: "settings", label: "Go to Settings", icon: Settings, run: go("/settings") },
      { id: "onboarding", label: "Go to Onboarding", icon: Rocket, run: go("/onboarding") },
      {
        id: "theme",
        label: theme === "dark" ? "Switch to light mode" : "Switch to dark mode",
        icon: theme === "dark" ? Sun : Moon,
        run: () => {
          toggleTheme()
          onOpenChange(false)
        },
      },
      {
        id: "refresh",
        label: "Reload page",
        icon: RefreshCw,
        run: () => {
          window.location.reload()
        },
      },
      {
        id: "logout",
        label: "Sign out",
        icon: LogOut,
        run: () => {
          logout()
          navigate("/auth/login")
          onOpenChange(false)
        },
      },
    ]
  }, [navigate, onOpenChange, theme, toggleTheme, logout])

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return actions
    return actions.filter((action) => action.label.toLowerCase().includes(q))
  }, [actions, query])

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown") {
      event.preventDefault()
      setActive((index) => Math.min(filtered.length - 1, index + 1))
    } else if (event.key === "ArrowUp") {
      event.preventDefault()
      setActive((index) => Math.max(0, index - 1))
    } else if (event.key === "Enter") {
      event.preventDefault()
      filtered[active]?.run()
    } else if (event.key === "Escape") {
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <div className="flex items-center gap-2 border-b border-neutral-200 px-4 dark:border-neutral-700">
          <Search className="h-4 w-4 text-neutral-400" />
          <input
            autoFocus
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setActive(0)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search…"
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-neutral-400"
          />
          <kbd className="rounded border border-neutral-200 px-1.5 py-0.5 text-[10px] text-neutral-400 dark:border-neutral-700">
            Esc
          </kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-1.5">
          {filtered.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-neutral-400">No commands found.</p>
          )}
          {filtered.map((action, index) => {
            const Icon = action.icon
            return (
              <button
                key={action.id}
                onMouseEnter={() => setActive(index)}
                onClick={action.run}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm",
                  index === active
                    ? "bg-brand-50 text-brand-800 dark:bg-brand-950/50 dark:text-brand-200"
                    : "text-neutral-700 hover:bg-neutral-50 dark:text-neutral-200 dark:hover:bg-neutral-800",
                )}
              >
                <Icon className="h-4 w-4" />
                {action.label}
              </button>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}