import * as React from "react"
import { useNavigate, useLocation, Outlet } from "react-router-dom"
import {
  LayoutDashboard,
  Mail,
  Users,
  Settings,
  Zap,
  FileText,
  BarChart2,
  LogOut,
  Search,
  Moon,
  Sun,
  Menu,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/authStore"
import { useThemeStore } from "@/store/themeStore"
import { useChannelHealth } from "@/hooks/useChannelHealth"
import { CommandPalette } from "./CommandPalette"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const navItems = [
  { name: "inbox", icon: Mail, label: "Inbox", href: "/inbox" },
  { name: "contacts", icon: Users, label: "Contacts", href: "/contacts" },
  { name: "channels", icon: Zap, label: "Channels", href: "/channels" },
  { name: "ai", icon: LayoutDashboard, label: "AI Agent", href: "/ai" },
  { name: "knowledge", icon: FileText, label: "Knowledge", href: "/knowledge" },
  { name: "analytics", icon: BarChart2, label: "Analytics", href: "/analytics" },
  { name: "settings", icon: Settings, label: "Settings", href: "/settings" },
]

export function Shell({ children }: { children?: React.ReactNode }) {
  const location = useLocation()
  const currentPath = location.pathname
  const isInbox = currentPath.startsWith("/inbox")
  const [paletteOpen, setPaletteOpen] = React.useState(false)

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setPaletteOpen((open) => !open)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950">
      <Sidebar currentPath={currentPath} onOpenPalette={() => setPaletteOpen(true)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenMobileNav={() => setPaletteOpen(true)}
        />
        <main
          className={cn(
            "min-h-0 flex-1 pb-16 md:pb-0",
            isInbox ? "overflow-hidden" : "overflow-y-auto bg-neutral-50 p-4 sm:p-6 dark:bg-neutral-950",
          )}
        >
          {children ?? <Outlet />}
        </main>
      </div>
      <MobileNav currentPath={currentPath} />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  )
}

function Sidebar({
  currentPath,
  onOpenPalette,
}: {
  currentPath: string
  onOpenPalette: () => void
}) {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const theme = useThemeStore((state) => state.theme)
  const toggleTheme = useThemeStore((state) => state.toggle)

  return (
    <aside className="hidden w-16 shrink-0 flex-col items-center bg-rail py-3 md:flex">
      <button
        onClick={() => navigate("/inbox")}
        className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white"
        title="TeleDesk"
      >
        TD
      </button>

      <nav className="mt-5 flex flex-1 flex-col items-center gap-1.5">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = currentPath === item.href
          return (
            <button
              key={item.name}
              onClick={() => navigate(item.href)}
              title={item.label}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
                active
                  ? "bg-brand-600 text-white"
                  : "text-brand-100/70 hover:bg-rail-hover hover:text-white",
              )}
            >
              <Icon className="h-5 w-5" />
            </button>
          )
        })}
      </nav>

      <div className="mt-2 flex flex-col items-center gap-1.5">
        <button
          onClick={onOpenPalette}
          title="Command palette (Ctrl/Cmd+K)"
          className="flex h-10 w-10 items-center justify-center rounded-xl text-brand-100/70 hover:bg-rail-hover hover:text-white"
        >
          <Search className="h-5 w-5" />
        </button>
        <button
          onClick={toggleTheme}
          title={theme === "dark" ? "Light mode" : "Dark mode"}
          className="flex h-10 w-10 items-center justify-center rounded-xl text-brand-100/70 hover:bg-rail-hover hover:text-white"
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
        <button
          onClick={logout}
          title="Sign out"
          className="flex h-10 w-10 items-center justify-center rounded-xl text-brand-100/70 hover:bg-rail-hover hover:text-white"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </aside>
  )
}

function Topbar({
  onOpenPalette,
  onOpenMobileNav,
}: {
  onOpenPalette: () => void
  onOpenMobileNav: () => void
}) {
  const { user, company, setLanguage, logout } = useAuthStore()
  const health = useChannelHealth()

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-neutral-200 bg-white px-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex min-w-0 items-center gap-3">
        <button
          onClick={onOpenMobileNav}
          className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 md:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
            {company?.name?.charAt(0) || "T"}
          </div>
          <span className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {company?.name || "TeleDesk"}
          </span>
        </div>

        <div
          className="hidden items-center gap-1.5 rounded-full border border-neutral-200 px-2.5 py-1 text-xs md:flex dark:border-neutral-700"
          title="Live channel health"
        >
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              health.tone === "ok"
                ? "bg-green-500"
                : health.tone === "warn"
                  ? "bg-amber-500"
                  : "bg-neutral-400",
            )}
          />
          <span className="text-neutral-600 dark:text-neutral-300">{health.label}</span>
        </div>

        <button
          onClick={onOpenPalette}
          className="hidden items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1.5 text-xs text-neutral-500 hover:bg-neutral-100 md:flex dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-400"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search or jump to…</span>
          <kbd className="ml-4 rounded border border-neutral-200 px-1 text-[10px] dark:border-neutral-600">
            Ctrl K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="outline" className="hidden sm:inline-flex">
          {health.total > 0 ? `${health.online}/${health.total} channels` : "No channels"}
        </Badge>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <Avatar className="h-5 w-5" />
              <span className="hidden sm:inline">{user?.name}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setLanguage("en")}>English</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setLanguage("ar")}>العربية</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-red-500">
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

function MobileNav({ currentPath }: { currentPath: string }) {
  const navigate = useNavigate()
  const items = navItems.slice(0, 4)
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex h-16 items-center justify-around border-t border-neutral-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden dark:border-neutral-800 dark:bg-neutral-900">
      {items.map((item) => {
        const Icon = item.icon
        const active = currentPath === item.href
        return (
          <button
            key={item.name}
            onClick={() => navigate(item.href)}
            className={cn(
              "flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px]",
              active ? "text-brand-600" : "text-neutral-500",
            )}
          >
            <Icon className="h-5 w-5" />
            {item.label}
          </button>
        )
      })}
    </nav>
  )
}