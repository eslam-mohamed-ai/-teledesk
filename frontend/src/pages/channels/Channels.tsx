import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Plus, Mail, Send, ShieldAlert, RefreshCw, Link as LinkIcon, X } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"

type Channel = {
  id: number
  provider: string
  external_id: string | null
  display_name: string | null
  status: string | null
  active: boolean
  capabilities: Record<string, any>
}

const PROVIDERS: { id: string; label: string; icon: React.ElementType; comingSoon: boolean }[] = [
  { id: "telegram", label: "Telegram", icon: Mail, comingSoon: false },
  { id: "messenger", label: "Messenger", icon: Send, comingSoon: false },
  { id: "whatsapp", label: "WhatsApp", icon: ShieldAlert, comingSoon: true },
  { id: "instagram", label: "Instagram", icon: LinkIcon, comingSoon: true },
]

export default function Channels() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: channels = [], isLoading } = useQuery<Channel[]>({
    queryKey: ["channels"],
    queryFn: async () => {
      const res = await api.get("/channels/")
      return res.data.items
    },
  })

  const connectMutation = useMutation({
    mutationFn: async ({ provider, payload }: { provider: string; payload: Record<string, any> }) => {
      const res = await api.post(`/channels/${provider}/connect`, { payload })
      return res.data.channel
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: async (channelId: number) => {
      await api.post(`/channels/${channelId}/disconnect`)
      return channelId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: async (channelId: number) => {
      const res = await api.post(`/channels/${channelId}/toggle`)
      return res.data.active
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })

  const statusBadge = (status: string | null) => {
    switch (status) {
      case "connected":
        return <Badge variant="brand">Connected</Badge>
      case "disconnected":
        return <Badge variant="destructive">Disconnected</Badge>
      case "needs_attention":
        return <Badge variant="secondary">Needs attention</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Channels</h1>
          <p className="text-neutral-500 dark:text-neutral-400">
            Connect messaging channels to receive customer conversations.
          </p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> {t("connect_channel")}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Connect a channel</DialogTitle>
              <DialogDescription>Select a provider and enter credentials.</DialogDescription>
            </DialogHeader>
            <DialogContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Provider
                  </label>
                  <div className="flex gap-2">
                    {PROVIDERS.map((p) => {
                      const Icon = p.icon
                      return (
                        <button
                          key={p.id}
                          onClick={() => handleConnect(p.id)}
                          disabled={p.comingSoon || connectMutation.isPending}
                          className={cn(
                            "flex flex-col items-center justify-center gap-2 rounded-lg border p-3 text-sm transition-colors",
                            p.comingSoon
                              ? "border-neutral-200 text-neutral-400 opacity-50"
                              : connectMutation.isPending
                              ? "border-brand-600 bg-brand-50 text-brand-700"
                              : "border-neutral-300 text-neutral-700 hover:border-brand-600 hover:bg-brand-50",
                          )}
                        >
                          <Icon className="h-5 w-5" />
                          <span>{p.label}</span>
                          {p.comingSoon && <span className="text-xs mt-1 text-neutral-400">Coming soon</span>}
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div className="text-xs text-neutral-500 mt-2">
                  Enter your Telegram bot token or Messenger page access token.
                </div>
              </div>
            </DialogContent>
            <DialogFooter>
              <Button variant="outline" onClick={() => connectMutation.reset()}>
                Cancel
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        </div>
      ) : channels.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <Mail className="mx-auto mb-4 h-12 w-12 text-neutral-400" />
            <h3 className="text-lg font-semibold text-neutral-900">No channels connected</h3>
            <p className="text-neutral-500 mt-2">
              Connect your first channel to start receiving customer messages.
            </p>
            <Button className="mt-4" onClick={() => connectMutation.reset()}>
              Connect channel
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {channels.map((channel) => (
            <Card key={channel.id}>
              <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-neutral-100 flex items-center justify-center text-neutral-600">
                    <Mail className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-neutral-900">
                      {channel.display_name || channel.provider}
                    </h3>
                    <p className="text-sm text-neutral-500">{channel.provider}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {statusBadge(channel.status)}
                  <Badge variant={channel.active ? "secondary" : "outline"}>
                    {channel.active ? "Active" : "Inactive"}
                  </Badge>
                  <button
                    onClick={() => toggleMutation.mutate(channel.id)}
                    disabled={toggleMutation.isPending}
                    className="text-xs text-brand-600 hover:underline"
                  >
                    {channel.active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => disconnectMutation.mutate(channel.id)}
                    disabled={disconnectMutation.isPending}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Disconnect
                  </button>
                </div>
              </CardContent>
              <CardFooter className="bg-transparent p-4 pt-0 border-t">
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  <span>Webhook: Ready</span>
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      }
    </div>
  )
}

function handleConnect(provider: string) {
  // Placeholder - in a real implementation this would open a provider-specific connect flow
  console.log("Connect", provider)
}
