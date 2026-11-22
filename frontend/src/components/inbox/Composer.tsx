import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Send, StickyNote, CornerDownLeft, AlertTriangle } from "lucide-react"
import { api, errorMessage } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Conversation, CannedReply, InternalNote, Message } from "@/types/inbox"

type Props = {
  conversation: Conversation
  onSent?: () => void
  onError?: (message: string) => void
}

export function Composer({ conversation, onSent, onError }: Props) {
  const queryClient = useQueryClient()
  const [value, setValue] = React.useState("")
  const [isNote, setIsNote] = React.useState(false)
  const [cannedOpen, setCannedOpen] = React.useState(false)
  const [activeCanned, setActiveCanned] = React.useState(0)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  const { data: cannedData } = useQuery<{ items: CannedReply[] }>({
    queryKey: ["canned-replies"],
    queryFn: async () => (await api.get("/conversations/canned-replies")).data,
    staleTime: 60_000,
  })
  const canned = cannedData?.items ?? []

  const filteredCanned = React.useMemo(() => {
    const query = value.replace(/^\//, "").trim().toLowerCase()
    if (!value.startsWith("/")) return []
    return canned
      .filter(
        (reply) =>
          !query ||
          reply.shortcut.toLowerCase().includes(query) ||
          reply.title.toLowerCase().includes(query) ||
          reply.body.toLowerCase().includes(query),
      )
      .slice(0, 6)
  }, [canned, value])

  React.useEffect(() => {
    setCannedOpen(value.startsWith("/") && filteredCanned.length > 0)
    setActiveCanned(0)
  }, [value, filteredCanned.length])

  const sendMutation = useMutation({
    mutationFn: async () => {
      const text = value.trim()
      const tempId = -Date.now()
      const now = new Date().toISOString()

      // Optimistic insert so the message appears immediately.
      if (isNote) {
        queryClient.setQueryData<InternalNote[]>(["notes", conversation.id], (old) => [
          { id: tempId, body: text, at: now },
          ...(old ?? []),
        ])
      } else {
        const optimistic: Message = {
          id: tempId,
          role: "agent",
          direction: "outbound",
          sender_type: "agent",
          content: text,
          content_type: "text",
          delivery_status: "sending",
          error_code: null,
          created_at: now,
        }
        queryClient.setQueryData<Message[]>(["messages", conversation.id], (old) => [
          ...(old ?? []),
          optimistic,
        ])
      }

      try {
        if (isNote) {
          await api.post(`/conversations/${conversation.id}/note`, { note: text })
        } else {
          await api.post(`/conversations/${conversation.id}/reply`, { text })
        }
        queryClient.invalidateQueries({ queryKey: ["messages", conversation.id] })
        queryClient.invalidateQueries({ queryKey: ["notes", conversation.id] })
        queryClient.invalidateQueries({ queryKey: ["conversations"] })
        setValue("")
        onSent?.()
      } catch (error) {
        // Roll back the optimistic entry and restore the text for retry.
        queryClient.setQueryData<Message[]>(["messages", conversation.id], (old) =>
          (old ?? []).filter((message) => message.id !== tempId),
        )
        queryClient.setQueryData<InternalNote[]>(["notes", conversation.id], (old) =>
          (old ?? []).filter((note) => note.id !== tempId),
        )
        setValue(text)
        onError?.(errorMessage(error))
      }
    },
  })

  const canSend = value.trim().length > 0 && (isNote || conversation.window_open)

  const submit = () => {
    if (!canSend || sendMutation.isPending) return
    sendMutation.mutate()
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (cannedOpen && filteredCanned.length > 0) {
      if (event.key === "ArrowDown") {
        event.preventDefault()
        setActiveCanned((index) => (index + 1) % filteredCanned.length)
        return
      }
      if (event.key === "ArrowUp") {
        event.preventDefault()
        setActiveCanned((index) => (index - 1 + filteredCanned.length) % filteredCanned.length)
        return
      }
      if (event.key === "Tab") {
        event.preventDefault()
        setValue(filteredCanned[activeCanned]?.body ?? value)
        setCannedOpen(false)
        return
      }
      if (event.key === "Escape") {
        setCannedOpen(false)
        return
      }
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-900">
      {!conversation.window_open && !isNote && (
        <div className="mb-2 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <AlertTriangle className="h-4 w-4" />
          <span>
            Messaging window closed
            {conversation.window_expires_at
              ? ` · reopened ${new Date(conversation.window_expires_at).toLocaleString()}`
              : ""}
          </span>
        </div>
      )}

      <div className="relative">
        {cannedOpen && (
          <div className="absolute bottom-full left-0 z-20 mb-2 w-full overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-lg dark:border-neutral-700 dark:bg-neutral-800">
            <div className="border-b border-neutral-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-neutral-400 dark:border-neutral-700">
              Canned replies
            </div>
            {filteredCanned.map((reply, index) => (
              <button
                key={reply.id}
                type="button"
                onMouseEnter={() => setActiveCanned(index)}
                onClick={() => {
                  setValue(reply.body)
                  setCannedOpen(false)
                  textareaRef.current?.focus()
                }}
                className={cn(
                  "block w-full px-3 py-2 text-left",
                  index === activeCanned
                    ? "bg-brand-50 dark:bg-brand-950/40"
                    : "hover:bg-neutral-50 dark:hover:bg-neutral-700/60",
                )}
              >
                <span className="text-xs font-semibold text-brand-700 dark:text-brand-300">
                  /{reply.shortcut}
                </span>
                <span className="ml-2 text-xs text-neutral-500 dark:text-neutral-400">{reply.title}</span>
                <span className="mt-0.5 block truncate text-xs text-neutral-500 dark:text-neutral-400">
                  {reply.body}
                </span>
              </button>
            ))}
          </div>
        )}

        <div
          className={cn(
            "flex items-end gap-2 rounded-xl border p-2 transition-colors",
            isNote
              ? "border-amber-300 bg-amber-50/60 dark:border-amber-700 dark:bg-amber-950/20"
              : "border-neutral-300 bg-white focus-within:border-brand-500 dark:border-neutral-700 dark:bg-neutral-800",
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            rows={1}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isNote ? "Add an internal note… (only your team sees this)" : "Type a message… (/ for canned replies)"}
            className="max-h-32 min-h-9 flex-1 resize-none bg-transparent px-1 py-1.5 text-sm text-neutral-900 outline-none placeholder:text-neutral-400 dark:text-neutral-100"
          />
          <div className="flex items-center gap-1">
            <button
              type="button"
              title={isNote ? "Switch to reply" : "Internal note"}
              onClick={() => setIsNote((note) => !note)}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
                isNote
                  ? "bg-amber-200 text-amber-900"
                  : "text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-700",
              )}
            >
              <StickyNote className="h-4 w-4" />
            </button>
            <Button
              size="sm"
              className={cn("h-8 gap-1 px-3", isNote && "bg-amber-500 hover:bg-amber-600")}
              onClick={submit}
              disabled={!canSend}
              isLoading={sendMutation.isPending}
            >
              <Send className="h-4 w-4" />
              <span className="hidden sm:inline">{isNote ? "Add note" : "Send"}</span>
            </Button>
          </div>
        </div>
        <div className="mt-1 flex items-center gap-2 px-1 text-[10px] text-neutral-400">
          <span className="flex items-center gap-1">
            <CornerDownLeft className="h-3 w-3" /> Enter to send
          </span>
          <span>Shift+Enter for a new line</span>
          <span className="ml-auto">{value.length}/4000</span>
        </div>
      </div>
    </div>
  )
}