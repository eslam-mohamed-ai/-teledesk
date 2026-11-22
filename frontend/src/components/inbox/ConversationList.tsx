import * as React from "react"
import { Bot, User, AlertCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { initials, relativeTime, providerLabel, statusLabel } from "@/lib/format"
import type { Conversation } from "@/types/inbox"

const ROW_HEIGHT = 76
const OVERSCAN = 6

type Props = {
  conversations: Conversation[]
  selectedId: number | null
  onSelect: (id: number) => void
  hasNextPage: boolean
  isFetchingNextPage: boolean
  onLoadMore: () => void
  isLoading: boolean
  resetKey: string
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  isLoading,
  resetKey,
}: Props) {
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = React.useState(0)
  const [viewport, setViewport] = React.useState(600)

  React.useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    setScrollTop(0)
    el.scrollTop = 0
    const update = () => setViewport(el.clientHeight || 600)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => observer.disconnect()
  }, [resetKey])

  const total = conversations.length
  const totalHeight = total * ROW_HEIGHT
  const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)
  const end = Math.min(total, Math.ceil((scrollTop + viewport) / ROW_HEIGHT) + OVERSCAN)
  const visible = conversations.slice(start, end)

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const el = event.currentTarget
    setScrollTop(el.scrollTop)
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 240 && hasNextPage && !isFetchingNextPage) {
      onLoadMore()
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center py-10">
        <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
      </div>
    )
  }

  if (total === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 text-center">
        <Bot className="mb-2 h-10 w-10 text-neutral-300" />
        <p className="text-sm font-medium text-neutral-600 dark:text-neutral-300">No conversations</p>
        <p className="mt-1 text-xs text-neutral-400">Try changing the filters.</p>
      </div>
    )
  }

  return (
    <div ref={scrollRef} onScroll={handleScroll} className="h-full overflow-y-auto">
      <div style={{ height: totalHeight, position: "relative" }}>
        <div style={{ transform: `translateY(${start * ROW_HEIGHT}px)` }}>
          {visible.map((conv) => {
            const active = conv.id === selectedId
            const provider = conv.channel_provider || conv.provider
            return (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelect(conv.id)}
                style={{ height: ROW_HEIGHT }}
                className={cn(
                  "flex w-full items-center gap-3 border-b border-neutral-100 px-3 text-left transition-colors dark:border-neutral-800",
                  active
                    ? "bg-brand-50 dark:bg-brand-950/40"
                    : "hover:bg-neutral-50 dark:hover:bg-neutral-800/60",
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                    active
                      ? "bg-brand-600 text-white"
                      : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
                  )}
                >
                  {initials(conv.contact_name)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                      {conv.contact_name || "Unknown contact"}
                    </p>
                    {conv.needs_human && (
                      <span className="flex items-center gap-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                        <AlertCircle className="h-3 w-3" /> Human
                      </span>
                    )}
                    <span className="ml-auto shrink-0 text-[11px] text-neutral-400">
                      {relativeTime(conv.last_message_at)}
                    </span>
                  </div>
                  <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">
                    {conv.last_preview || "No messages yet"}
                  </p>
                  <div className="mt-1 flex items-center gap-1.5">
                    <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                      {providerLabel(provider)}
                    </span>
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5 text-[10px] font-medium",
                        conv.status === "closed"
                          ? "bg-neutral-200 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300"
                          : conv.ai_handling
                            ? "bg-brand-100 text-brand-700"
                            : "bg-indigo-100 text-indigo-700",
                      )}
                    >
                      {statusLabel(conv.status)}
                    </span>
                    {conv.unread_count > 0 && (
                      <span className="ml-auto flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-brand-600" />
                        <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-bold text-white">
                          {conv.unread_count > 99 ? "99+" : conv.unread_count}
                        </span>
                      </span>
                    )}
                  </div>
                </div>
                {conv.ai_handling ? (
                  <Bot className="h-4 w-4 shrink-0 text-neutral-400" />
                ) : (
                  <User className="h-4 w-4 shrink-0 text-neutral-400" />
                )}
              </button>
            )
          })}
        </div>
      </div>
      {isFetchingNextPage && (
        <div className="flex justify-center py-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        </div>
      )}
    </div>
  )
}

export { ROW_HEIGHT }