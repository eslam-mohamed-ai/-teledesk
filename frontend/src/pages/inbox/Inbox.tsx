import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Search, Mail, Clock, User, Bot, AlertCircle, Send, ChevronRight } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"

type Conversation = {
  id: number
  channel_provider: string | null
  contact_name: string | null
  status: string | null
  last_message_at: string | null
  unread_count: number
  assigned_to: string | null
  ai_handling: boolean
  needs_human: boolean
}

type Message = {
  id: number
  direction: "inbound" | "outbound"
  content: string
  created_at: string
  sender_name: string | null
  status: string | null
}

const TABS: { id: string; label: string }[] = [
  { id: "all", label: "All" },
  { id: "mine", label: "Mine" },
  { id: "unassigned", label: "Unassigned" },
  { id: "closed", label: "Closed" },
]

export default function Inbox() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [tab, setTab] = React.useState<string>("all")
  const [selectedConvId, setSelectedConvId] = React.useState<number | null>(null)

  const { data: conversations = [], isLoading } = useQuery<Conversation[]>({
    queryKey: ["conversations", tab],
    queryFn: async () => {
      const res = await api.get("/conversations/", { params: { tab } })
      return res.data.items
    },
  })

  const messagesQuery = useQuery<Message[]>({
    queryKey: ["messages", selectedConvId],
    queryFn: async () => {
      if (!selectedConvId) return []
      const res = await api.get(`/conversations/${selectedConvId}/messages`)
      return res.data.items
    },
    enabled: !!selectedConvId,
  })

  const sendMessageMutation = useMutation({
    mutationFn: async ({ convId, content }: { convId: number; content: string }) => {
      const res = await api.post(`/conversations/${convId}/messages`, { content })
      return res.data
    },
    onSuccess: (_, { convId }) => {
      queryClient.invalidateQueries({ queryKey: ["messages", convId] })
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
    },
  })

  const takeOverMutation = useMutation({
    mutationFn: async (convId: number) => {
      const res = await api.post(`/conversations/${convId}/take-over`)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
    },
  })

  return (
    <div className="flex h-full w-full">
      {/* Left: conversation list */}
      <div className="flex flex-col h-full border-r border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900">
        <div className="h-12 border-b border-neutral-200 bg-white px-4 dark:border-neutral-700 dark:bg-neutral-900">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
            <input
              type="text"
              placeholder={t("search_conversations")}
              className="h-8 w-full pl-9 pr-3 rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600 dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100 dark:focus:ring-brand-500"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <Tabs defaultValue="all" onValueChange={(value) => setTab(value)}>
            <TabsList className="grid w-full grid-cols-4 gap-1 p-1 mb-3">
              {TABS.map((tabItem) => (
                <TabsTrigger key={tabItem.id} value={tabItem.id} className="px-2 py-1.5 text-xs rounded-lg text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800 data-[state=active]:bg-brand-600 data-[state=active]:text-white">
                  {tabItem.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center px-4">
              <Mail className="h-10 w-10 text-neutral-400 mb-2" />
              <p className="text-sm text-neutral-500">{t("no_conversations")}</p>
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => setSelectedConvId(conv.id)}
                  className={cn(
                    "flex items-center justify-between gap-2 px-3 py-2 rounded-lg border text-left transition-colors",
                    selectedConvId === conv.id
                      ? "bg-brand-50 border-brand-200 dark:bg-brand-900/30 dark:border-brand-500"
                      : "bg-neutral-50 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-700",
                  )}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    {conv.ai_handling ? (
                      <Bot className="h-4 w-4 text-neutral-500" />
                    ) : (
                      <User className="h-4 w-4 text-neutral-500" />
                    )}
                    <div className="flex flex-col min-w-0">
                      <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                        {conv.contact_name || "Unknown contact"}
                      </p>
                      <p className="text-xs text-neutral-500 truncate">
                        {conv.channel_provider || "Channel"} · {conv.unread_count > 0 ? `${conv.unread_count} unread` : "Read"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {conv.unread_count > 0 && (
                      <div className="h-2 w-2 rounded-full bg-brand-600" />
                    )}
                    <Badge variant={conv.status === "closed" ? "destructive" : "brand"} className="text-xs">
                      {conv.status}
                    </Badge>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right: conversation detail */}
      <div className="flex-1 flex flex-col h-full bg-neutral-50 dark:bg-neutral-950">
        {!selectedConvId ? (
          <div className="flex-1 flex items-center justify-center p-12 text-center">
            <div>
              <Mail className="mx-auto mb-4 h-12 w-12 text-neutral-400" />
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Select a conversation</h3>
              <p className="text-neutral-500 dark:text-neutral-400 mt-1">
                Pick a conversation from the list to view and reply.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="h-10 border-b border-neutral-200 bg-white px-4 dark:border-neutral-700 dark:bg-neutral-900 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-600">
                  <User className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    {/* conversation name */}
                    {conversations.find((c) => c.id === selectedConvId)?.contact_name || "Unknown contact"}
                  </p>
                  <p className="text-xs text-neutral-500">Customer • Telegram</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => takeOverMutation.mutate(selectedConvId!)}>
                  <AlertCircle className="h-4 w-4 mr-1" /> {t("take_over")}
                </Button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messagesQuery.isLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
                </div>
              ) : messagesQuery.data?.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-center">
                  <p className="text-neutral-500 text-sm">No messages yet. Start the conversation.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {messagesQuery.data.map((msg) => (
                    <div
                      key={msg.id}
                      className={cn(
                        "flex flex-col max-w-[80%]",
                        msg.direction === "outbound" ? "items-end" : "items-start",
                      )}
                    >
                      <div className={cn(
                        "rounded-lg px-4 py-2 text-sm shadow-sm",
                        msg.direction === "outbound"
                          ? "bg-brand-600 text-white rounded-tr-none"
                          : "bg-white text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100 rounded-tl-none",
                      )}>
                        {msg.content}
                      </div>
                      <span className={cn("text-[10px] mt-0.5", msg.direction === "outbound" ? "ml-auto text-brand-500" : "text-neutral-400")}>
                        {msg.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="border-t border-neutral-200 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-900">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Type a message..."
                  className="flex-1 h-10 rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600 dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100 dark:focus:ring-brand-500"
                />
                <Button onClick={() => {}} disabled className="px-4">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
