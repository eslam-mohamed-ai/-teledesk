import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { Channel } from "@/types/inbox"

export type ChannelHealth = {
  total: number
  online: number
  hasIssues: boolean
  label: string
  tone: "ok" | "warn" | "idle"
}

export function useChannelHealth(): ChannelHealth {
  const { data } = useQuery<{ items: Channel[] }>({
    queryKey: ["channels"],
    queryFn: async () => (await api.get("/channels/")).data,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const channels = data?.items ?? []
  const online = channels.filter((channel) => channel.active && channel.status === "connected").length
  const hasIssues = channels.some(
    (channel) => channel.status === "disconnected" || channel.status === "needs_attention",
  )

  if (channels.length === 0) {
    return { total: 0, online: 0, hasIssues: false, label: "No channels", tone: "idle" }
  }
  if (hasIssues || online === 0) {
    return { total: channels.length, online, hasIssues: true, label: "Channels need attention", tone: "warn" }
  }
  return { total: channels.length, online, hasIssues: false, label: `${online} online`, tone: "ok" }
}