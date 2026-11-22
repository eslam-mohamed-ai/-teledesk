import * as React from "react"
import {
  Bot,
  Check,
  CheckCheck,
  Clock,
  AlertCircle,
  StickyNote,
  RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { dayKey, dayLabel, formatTime } from "@/lib/format"
import type { InternalNote, Message } from "@/types/inbox"

type ThreadItem =
  | { kind: "message"; at: string; message: Message }
  | { kind: "note"; at: string; note: InternalNote }

type Props = {
  messages: Message[]
  notes: InternalNote[]
  isLoading: boolean
  onRetry: (messageId: number) => void
}

function sortValue(item: ThreadItem): number {
  const raw = item.at ? new Date(item.at).getTime() : 0
  return Number.isNaN(raw) ? 0 : raw
}

function DeliveryTicks({ status }: { status: string | null }) {
  if (!status) return null
  if (status === "failed") {
    return (
      <span className="flex items-center gap-1 text-[10px] font-medium text-red-500">
        <AlertCircle className="h-3 w-3" /> Failed
      </span>
    )
  }
  if (status === "read") {
    return <CheckCheck className="h-3 w-3 text-brand-500" />
  }
  if (status === "delivered") {
    return <CheckCheck className="h-3 w-3 text-brand-400" />
  }
  if (status === "sent") {
    return <Check className="h-3 w-3 text-brand-400" />
  }
  return <Clock className="h-3 w-3 text-neutral-400" />
}

export function MessageThread({ messages, notes, isLoading, onRetry }: Props) {
  const items = React.useMemo<ThreadItem[]>(() => {
    const messageItems: ThreadItem[] = messages.map((message) => ({
      kind: "message",
      at: message.created_at || "",
      message,
    }))
    const noteItems: ThreadItem[] = notes.map((note) => ({
      kind: "note",
      at: note.at || "",
      note,
    }))
    return [...messageItems, ...noteItems].sort((a, b) => sortValue(a) - sortValue(b))
  }, [messages, notes])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 text-center">
        <Bot className="mb-2 h-10 w-10 text-neutral-300" />
        <p className="text-sm font-medium text-neutral-600 dark:text-neutral-300">No messages yet</p>
        <p className="mt-1 text-xs text-neutral-400">Send the first message to start the conversation.</p>
      </div>
    )
  }

  let lastDay = ""

  return (
    <div className="space-y-2 px-4 py-4">
      {items.map((item) => {
        const at = item.at
        const currentDay = dayKey(at)
        const showDay = currentDay !== lastDay
        lastDay = currentDay

        if (item.kind === "note") {
          return (
            <React.Fragment key={`note-${item.note.id}`}>
              {showDay && <DaySeparator label={dayLabel(at)} />}
              <div className="flex justify-center">
                <div className="max-w-[85%] rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                  <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">
                    <StickyNote className="h-3 w-3" /> Internal note · {formatTime(at)}
                  </div>
                  <p className="whitespace-pre-wrap">{item.note.body}</p>
                </div>
              </div>
            </React.Fragment>
          )
        }

        const message = item.message
        const isOutbound = message.direction === "outbound"
        const isAI = message.role === "bot" || message.sender_type === "ai"
        const isSystem = message.role === "system" || message.sender_type === "system"

        if (isSystem) {
          return (
            <React.Fragment key={`msg-${message.id}`}>
              {showDay && <DaySeparator label={dayLabel(at)} />}
              <div className="flex justify-center">
                <p className="rounded-full bg-neutral-100 px-3 py-1 text-[11px] text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
                  {message.content}
                </p>
              </div>
            </React.Fragment>
          )
        }

        return (
          <React.Fragment key={`msg-${message.id}`}>
            {showDay && <DaySeparator label={dayLabel(at)} />}
            <div className={cn("flex flex-col", isOutbound ? "items-end" : "items-start")}>
              {isAI && (
                <div className="mb-0.5 flex items-center gap-1 text-[10px] font-semibold text-violet-600 dark:text-violet-400">
                  <Bot className="h-3 w-3" /> AI assistant
                </div>
              )}
              <div
                className={cn(
                  "max-w-[80%] rounded-xl px-3 py-2 text-sm shadow-sm",
                  isAI
                    ? "rounded-tr-none bg-violet-100 text-violet-950 dark:bg-violet-950/40 dark:text-violet-100"
                    : isOutbound
                      ? "rounded-tr-none bg-brand-600 text-white"
                      : "rounded-tl-none border border-neutral-200 bg-white text-neutral-900 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100",
                )}
              >
                <p className="whitespace-pre-wrap break-words">{message.content}</p>
              </div>
              <div
                className={cn(
                  "mt-0.5 flex items-center gap-1.5 text-[10px] text-neutral-400",
                  isOutbound ? "flex-row-reverse" : "",
                )}
              >
                <span>{formatTime(at)}</span>
                {isOutbound && <DeliveryTicks status={message.delivery_status} />}
                {message.delivery_status === "failed" && (
                  <button
                    type="button"
                    onClick={() => onRetry(message.id)}
                    className="ml-1 flex items-center gap-1 rounded bg-red-50 px-1.5 py-0.5 font-medium text-red-600 hover:bg-red-100"
                  >
                    <RefreshCw className="h-3 w-3" /> Retry
                  </button>
                )}
              </div>
            </div>
          </React.Fragment>
        )
      })}
    </div>
  )
}

function DaySeparator({ label }: { label: string }) {
  return (
    <div className="my-3 flex items-center gap-3">
      <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
      <span className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-[10px] font-medium text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
        {label}
      </span>
      <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
    </div>
  )
}