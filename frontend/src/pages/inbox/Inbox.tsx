import * as React from "react"
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import {
  ArrowLeft,
  Bot,
  Check,
  ChevronDown,
  Mail,
  Search,
  User,
  UserCheck,
  X,
  AlertTriangle,
  Info,
} from "lucide-react"
import { api, errorMessage } from "@/lib/api"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ConversationList } from "@/components/inbox/ConversationList"
import { MessageThread } from "@/components/inbox/MessageThread"
import { Composer } from "@/components/inbox/Composer"
import { ContactPanel } from "@/components/inbox/ContactPanel"
import { useRealtime } from "@/hooks/useRealtime"
import { cn } from "@/lib/utils"
import { providerLabel, statusLabel } from "@/lib/format"
import { useTranslation } from "@/lib/i18n-react"
import type {
  Channel,
  Conversation,
  ConversationPage,
  InternalNote,
  Member,
  Message,
  MessagePage,
} from "@/types/inbox"

type Tab = "all" | "mine" | "unassigned" | "closed"
type MobileView = "list" | "thread" | "contact"

const TABS: { id: Tab; label: string }[] = [
  { id: "all", label: "all" },
  { id: "mine", label: "mine" },
  { id: "unassigned", label: "unassigned" },
  { id: "closed", label: "closed" },
]

export default function Inbox() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [tab, setTab] = React.useState<Tab>("all")
  const [channel, setChannel] = React.useState<string>("")
  const [unreadOnly, setUnreadOnly] = React.useState(false)
  const [needsHumanOnly, setNeedsHumanOnly] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const [selectedId, setSelectedId] = React.useState<number | null>(null)
  const [mobileView, setMobileView] = React.useState<MobileView>("list")
  const [showContact, setShowContact] = React.useState(true)

  useRealtime(true)

  const channelsQuery = useQuery<{ items: Channel[] }>({
    queryKey: ["channels"],
    queryFn: async () => (await api.get("/channels/")).data,
  })

  const membersQuery = useQuery<Member[]>({
    queryKey: ["team-members"],
    queryFn: async () => (await api.get("/team/members")).data,
  })

  const filters = React.useMemo(() => {
    const params: Record<string, string> = { limit: "50" }
    if (needsHumanOnly) {
      params.status = "needs_human"
    } else if (tab === "closed") {
      params.status = "closed"
    } else {
      params.status = "all"
    }
    if (tab === "mine") params.assignee = "me"
    else if (tab === "unassigned") params.assignee = "unassigned"
    else params.assignee = "all"
    if (channel) params.channel = channel
    if (unreadOnly) params.unread = "true"
    if (search.trim()) params.q = search.trim()
    return params
  }, [tab, channel, unreadOnly, needsHumanOnly, search])

  const conversationsQuery = useInfiniteQuery<ConversationPage>({
    queryKey: ["conversations", filters],
    queryFn: async ({ pageParam }) => {
      const params = { ...filters }
      if (pageParam) params.before = String(pageParam)
      const res = await api.get<ConversationPage>("/conversations/", { params })
      return res.data
    },
    initialPageParam: undefined as number | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  })

  const conversations = React.useMemo(
    () => conversationsQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [conversationsQuery.data],
  )

  const selectedConversation = React.useMemo(
    () => conversations.find((conversation) => conversation.id === selectedId) ?? null,
    [conversations, selectedId],
  )

  const messagesQuery = useQuery<MessagePage>({
    queryKey: ["messages", selectedId],
    queryFn: async () => {
      const res = await api.get<MessagePage>(`/conversations/${selectedId}/messages`, {
        params: { limit: 100 },
      })
      return res.data
    },
    enabled: !!selectedId,
  })

  const notesQuery = useQuery<{ items: InternalNote[] }>({
    queryKey: ["notes", selectedId],
    queryFn: async () => (await api.get(`/conversations/${selectedId}/notes`)).data,
    enabled: !!selectedId,
  })

  const patchConversation = React.useCallback(
    (id: number, patch: Partial<Conversation>) => {
      queryClient.setQueriesData<ConversationPage>({ queryKey: ["conversations"] }, (page) => {
        if (!page) return page
        return {
          ...page,
          items: page.items.map((conversation) =>
            conversation.id === id ? { ...conversation, ...patch } : conversation,
          ),
        }
      })
    },
    [queryClient],
  )

  const invalidate = React.useCallback(
    (id?: number) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
      if (id) {
        queryClient.invalidateQueries({ queryKey: ["messages", id] })
        queryClient.invalidateQueries({ queryKey: ["notes", id] })
      }
    },
    [queryClient],
  )

  const actionMutation = useMutation({
    mutationFn: async ({ id, action }: { id: number; action: string }) => {
      await api.post(`/conversations/${id}/${action}`)
      return { id, action }
    },
    onSuccess: ({ id, action }) => {
      const patch: Partial<Conversation> =
        action === "close"
          ? { status: "closed" }
          : action === "reopen" || action === "hand-back"
            ? { status: "open" }
            : action === "take"
              ? { status: "human" }
              : {}
      patchConversation(id, patch)
      invalidate(id)
    },
    onError: (error) => {
      window.alert(errorMessage(error))
      invalidate()
    },
  })

  const assignMutation = useMutation({
    mutationFn: async ({ id, assignee }: { id: number; assignee: number | null }) => {
      await api.post(`/conversations/${id}/assign`, { assignee_user_id: assignee })
      return { id, assignee }
    },
    onSuccess: ({ id, assignee }) => {
      const member = membersQuery.data?.find((m) => m.id === assignee)
      patchConversation(id, { assignee_user_id: assignee, assignee_name: member?.name ?? null })
      invalidate(id)
    },
  })

  const readMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/conversations/${id}/read`)
      return id
    },
    onSuccess: (id) => patchConversation(id, { unread_count: 0 }),
  })

  const retryMutation = useMutation({
    mutationFn: async ({ cid, mid }: { cid: number; mid: number }) => {
      await api.post(`/conversations/${cid}/messages/${mid}/retry`)
      return cid
    },
    onSuccess: (cid) => invalidate(cid),
  })

  const selectConversation = (id: number) => {
    setSelectedId(id)
    setMobileView("thread")
    const target = conversations.find((conversation) => conversation.id === id)
    if (target && target.unread_count > 0) readMutation.mutate(id)
  }

  const closeMobile = () => setMobileView("list")

  return (
    <div className="flex h-full overflow-hidden bg-white dark:bg-neutral-900">
      {/* Conversation list */}
      <section
        className={cn(
          "flex h-full w-full shrink-0 flex-col border-r border-neutral-200 dark:border-neutral-800 md:w-80 lg:w-96",
          mobileView !== "list" && "hidden md:flex",
        )}
      >
        <div className="border-b border-neutral-200 p-3 dark:border-neutral-800">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("search_conversations")}
              className="h-9 w-full rounded-lg border border-neutral-200 bg-neutral-50 pl-9 pr-3 text-sm outline-none focus:border-brand-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
            />
          </div>

          <Tabs value={tab} onValueChange={(value) => setTab(value as Tab)} className="mt-3">
            <TabsList className="grid w-full grid-cols-4 gap-1">
              {TABS.map((item) => (
                <TabsTrigger key={item.id} value={item.id} className="px-2 py-1.5 text-xs">
                  {t(item.label)}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <div className="relative">
              <select
                value={channel}
                onChange={(event) => setChannel(event.target.value)}
                className="h-7 rounded-md border border-neutral-200 bg-white px-2 text-xs outline-none focus:border-brand-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
              >
                <option value="">{t("all_channels")}</option>
                {(channelsQuery.data?.items ?? []).map((item) => (
                  <option key={item.id} value={String(item.id)}>
                    {item.display_name || providerLabel(item.provider)}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => setUnreadOnly((value) => !value)}
              className={cn(
                "h-7 rounded-md border px-2 text-xs font-medium transition-colors",
                unreadOnly
                  ? "border-brand-600 bg-brand-600 text-white"
                  : "border-neutral-200 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800",
              )}
            >
              {t("unread")}
            </button>
            <button
              type="button"
              onClick={() => setNeedsHumanOnly((value) => !value)}
              className={cn(
                "flex h-7 items-center gap-1 rounded-md border px-2 text-xs font-medium transition-colors",
                needsHumanOnly
                  ? "border-amber-500 bg-amber-500 text-white"
                  : "border-neutral-200 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800",
              )}
            >
              <AlertTriangle className="h-3 w-3" /> {t("needs_human")}
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1">
          <ConversationList
            conversations={conversations}
            selectedId={selectedId}
            onSelect={selectConversation}
            hasNextPage={!!conversationsQuery.hasNextPage}
            isFetchingNextPage={conversationsQuery.isFetchingNextPage}
            onLoadMore={() => void conversationsQuery.fetchNextPage()}
            isLoading={conversationsQuery.isLoading}
            resetKey={`${tab}|${channel}|${unreadOnly}|${needsHumanOnly}|${search}`}
          />
        </div>
      </section>

      {/* Thread */}
      <section
        className={cn(
          "flex h-full min-w-0 flex-1 flex-col bg-neutral-50 dark:bg-neutral-950",
          mobileView === "list" && "hidden md:flex",
          mobileView === "contact" && "hidden xl:flex",
        )}
      >
        {!selectedConversation ? (
          <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
            <Mail className="mb-3 h-12 w-12 text-neutral-300" />
            <h3 className="text-base font-semibold text-neutral-700 dark:text-neutral-200">
              {t("select_conversation")}
            </h3>
            <p className="mt-1 text-sm text-neutral-500">{t("choose_conversation_to_reply")}</p>
          </div>
        ) : (
          <>
            <header className="flex h-14 shrink-0 items-center gap-2 border-b border-neutral-200 bg-white px-3 dark:border-neutral-800 dark:bg-neutral-900">
              <button
                onClick={closeMobile}
                className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 md:hidden"
                aria-label={t("back_to_list")}
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
                {(selectedConversation.contact_name || "?").slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {selectedConversation.contact_name || t("unknown_contact")}
                </p>
                <div className="flex items-center gap-1.5 text-[11px] text-neutral-500">
                  <span>{providerLabel(selectedConversation.channel_provider || selectedConversation.provider)}</span>
                  <span>·</span>
                  <span>{statusLabel(selectedConversation.status)}</span>
                  {selectedConversation.needs_human && (
                    <span className="rounded bg-amber-100 px-1 text-[10px] font-semibold text-amber-700">
                      {t("needs_human")}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                {selectedConversation.ai_handling ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 px-2 text-xs"
                    onClick={() => actionMutation.mutate({ id: selectedConversation.id, action: "take" })}
                  >
                    <UserCheck className="mr-1 h-3.5 w-3.5" />
                    <span className="hidden sm:inline">{t("take_over")}</span>
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 px-2 text-xs"
                    onClick={() => actionMutation.mutate({ id: selectedConversation.id, action: "hand-back" })}
                  >
                    <Bot className="mr-1 h-3.5 w-3.5" />
                    <span className="hidden sm:inline">{t("hand_back")}</span>
                  </Button>
                )}

                <div className="relative hidden sm:block">
                  <select
                    value={selectedConversation.assignee_user_id ?? ""}
                    onChange={(event) =>
                      assignMutation.mutate({
                        id: selectedConversation.id,
                        assignee: event.target.value ? Number(event.target.value) : null,
                      })
                    }
                    className="h-8 max-w-32 rounded-md border border-neutral-200 bg-white px-2 text-xs outline-none focus:border-brand-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                  >
                    <option value="">{t("unassigned")}</option>
                    {(membersQuery.data ?? []).map((member) => (
                      <option key={member.id} value={String(member.id)}>
                        {member.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-neutral-400" />
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 px-2 text-xs"
                  onClick={() =>
                    actionMutation.mutate({
                      id: selectedConversation.id,
                      action: selectedConversation.status === "closed" ? "reopen" : "close",
                    })
                  }
                >
                  {selectedConversation.status === "closed" ? t("reopen_conversation") : t("close_conversation")}
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 px-2 text-xs"
                  onClick={() => {
                    setShowContact((value) => !value)
                    setMobileView(mobileView === "contact" ? "thread" : "contact")
                  }}
                >
                  <Info className="h-4 w-4" />
                </Button>
              </div>
            </header>

            {!selectedConversation.window_open && (
              <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                <span>{t("window_closed")}</span>
                {selectedConversation.window_expires_at && (
                  <span className="text-amber-600">
                    · {t("reopened_at")} {new Date(selectedConversation.window_expires_at).toLocaleString()}
                  </span>
                )}
              </div>
            )}

            <div className="min-h-0 flex-1 overflow-y-auto">
              <MessageThread
                messages={messagesQuery.data?.items ?? []}
                notes={notesQuery.data?.items ?? []}
                isLoading={messagesQuery.isLoading}
                onRetry={(mid) => retryMutation.mutate({ cid: selectedConversation.id, mid })}
              />
            </div>

            <Composer
              key={selectedConversation.id}
              conversation={selectedConversation}
              onError={(message) => window.alert(message)}
            />
          </>
        )}
      </section>

      {/* Contact panel */}
      {showContact && selectedConversation && (
        <div
          className={cn(
            "h-full shrink-0 [&>aside]:w-full xl:[&>aside]:w-80",
            mobileView === "contact" ? "flex w-full" : "hidden xl:flex",
          )}
        >
          <ContactPanel
            conversation={selectedConversation}
            onClose={() => {
              setShowContact(false)
              setMobileView("thread")
            }}
          />
        </div>
      )}
    </div>
  )
}
