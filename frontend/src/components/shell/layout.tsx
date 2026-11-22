import * as React from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { useAuthStore } from "@/store/authStore"
import { LayoutDashboard, Mail, Users, Settings, Zap, FileText, BarChart2, LogOut } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
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
  { name: "ai", icon: Zap, label: "AI Agent", href: "/ai" },
  { name: "knowledge", icon: FileText, label: "Knowledge", href: "/knowledge" },
  { name: "analytics", icon: BarChart2, label: "Analytics", href: "/analytics" },
  { name: "settings", icon: Settings, label: "Settings", href: "/settings" },
]

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, company, setLanguage, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const currentPath = location.pathname

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar currentPath={currentPath} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar user={user} company={company} setLanguage={setLanguage} logout={logout} />
        <main className="flex-1 overflow-y-auto bg-neutral-50 p-6">{children}</main>
      </div>
    </div>
  )
}

function Sidebar({ currentPath }: { currentPath: string }) {
  const navigate = useNavigate()
  const { logout } = useAuthStore()

  return (
    <aside className="flex w-16 flex-col shrink-0 border-r border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900 p-3">
      <div className="flex h-10 w-full items-center justify-center rounded-lg text-brand-600 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
        <LayoutDashboard className="h-6 w-6" />
      </div>
      <nav className="mt-4 flex flex-col gap-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = currentPath === item.href
          return (
            <button
              key={item.name}
              onClick={() => navigate(item.href)}
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-lg p-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400"
                  : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800",
              )}
            >
              <Icon className="h-5 w-5" />
            </button>
          )
        })}
      </nav>
      <div className="mt-auto flex flex-col gap-1">
        <button
          onClick={() => navigate("/settings")}
          className="flex w-full items-center justify-center gap-2 rounded-lg p-2 text-sm font-medium text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800 transition-colors"
        >
          <Settings className="h-5 w-5" />
        </button>
        <button
          onClick={logout}
          className="flex w-full items-center justify-center gap-2 rounded-lg p-2 text-sm font-medium text-neutral-600 hover:bg-red-50 dark:text-neutral-400 dark:hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </aside>
  )
}

function Topbar({ user, company, setLanguage, logout }: any) {
  return (
    <header className="flex h-12 items-center justify-between border-b border-neutral-200 bg-white px-6 dark:border-neutral-700 dark:bg-neutral-900">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 font-semibold text-xs">
            {company?.name?.charAt(0) || "T"}
          </div>
          <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {company?.name || "TeleDesk"}
          </span>
        </div>
        <div className="hidden md:flex items-center gap-4 pl-6 border-l border-neutral-200 dark:border-neutral-700">
          <div className="relative w-64">
            <input
              type="text"
              placeholder="Search conversations..."
              className="h-9 w-full rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600 dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100 dark:focus:ring-brand-500"
            />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" className="px-2">
          <BarChart2 className="mr-2 h-4 w-4" /> Analytics
        </Button>
        <div className="relative">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Avatar src={undefined} className="mr-2" />
                {user?.name}
                <span className="hidden sm:inline ml-2 text-xs text-neutral-500">{user?.role}</span>
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
      </div>
    </header>
  )
}
