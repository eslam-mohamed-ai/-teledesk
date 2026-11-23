import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Plug, Zap } from "lucide-react"
import { api, errorMessage } from "@/lib/api"
import { apiClient } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { ChannelCard } from "@/components/channels/ChannelCard"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"
import type { Channel, ProviderMetadata } from "@/types/inbox"

export default function Channels() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [open, setOpen] = React.useState(false)
  const [selected, setSelected] = React.useState<string>("telegram")
  const [payload, setPayload] = React.useState<Record<string, string>>({})
  const [error, setError] = React.useState("")

  const channelsQuery = useQuery<{ items: Channel[] }>({
    queryKey: ["channels"],
    queryFn: async () => (await apiClient.channels.list()).data,
  })

  const providersQuery = useQuery<{ items: ProviderMetadata[] }>({
    queryKey: ["channel-providers"],
    queryFn: async () => (await apiClient.channels.providers()).data,
    staleTime: 5 * 60_000,
  })

  const providers = providersQuery.data?.items ?? []
  const selectedProvider = providers.find((provider) => provider.id === selected) ?? providers[0]

  const connectMutation = useMutation({
    mutationFn: async ({ provider, values }: { provider: string; values: Record<string, string> }) => {
      const res = await api.post(`/channels/${provider}/connect`, { payload: values })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      setOpen(false)
      setPayload({})
      setError("")
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  })

  const toggleMutation = useMutation({
    mutationFn: async (channel: Channel) => {
      const res = await api.post(`/channels/${channel.id}/toggle`)
      return res.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channels"] }),
  })

  const disconnectMutation = useMutation({
    mutationFn: async (channel: Channel) => {
      await api.post(`/channels/${channel.id}/disconnect`)
      return channel.id
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channels"] }),
  })

  const channels = channelsQuery.data?.items ?? []
  const labelFor = (provider: string) =>
    providers.find((item) => item.id === provider)?.label ??
    provider.charAt(0).toUpperCase() + provider.slice(1)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{t("channels")}</h1>
          <p className="text-neutral-500 dark:text-neutral-400">
            Connect messaging channels to receive customer conversations.
          </p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> {t("connect_channel")}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("connect_channel")}</DialogTitle>
              <DialogDescription>
                Choose a provider and enter its credentials. Providers marked “Coming soon” cannot be
                connected yet.
              </DialogDescription>
            </DialogHeader>

            {providersQuery.isLoading ? (
              <p className="py-6 text-center text-sm text-neutral-500">Loading providers…</p>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {providers.map((provider) => {
                    const disabled = !provider.available
                    return (
                      <button
                        key={provider.id}
                        type="button"
                        disabled={disabled}
                        onClick={() => {
                          setSelected(provider.id)
                          setPayload({})
                          setError("")
                        }}
                        className={cn(
                          "rounded-xl border p-3 text-left transition-colors",
                          selected === provider.id
                            ? "border-brand-600 bg-brand-50 dark:bg-brand-950/30"
                            : "border-neutral-200 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800",
                          disabled && "cursor-not-allowed opacity-50",
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold">{provider.label}</span>
                          {!provider.available && (
                            <Badge variant="outline" className="text-[10px]">
                              {t("coming_soon")}
                            </Badge>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-neutral-500">{provider.description}</p>
                      </button>
                    )
                  })}
                </div>

                {selectedProvider?.available && (
                  <div className="space-y-2">
                    {selectedProvider.fields.map((field) => (
                      <Input
                        key={field.key}
                        label={field.label}
                        type={field.type === "password" ? "password" : "text"}
                        value={payload[field.key] || ""}
                        onChange={(event) =>
                          setPayload((prev) => ({ ...prev, [field.key]: event.target.value }))
                        }
                      />
                    ))}
                    {error && <p className="text-xs text-red-600">{error}</p>}
                  </div>
                )}
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (!selectedProvider) return
                  connectMutation.mutate({ provider: selectedProvider.id, values: payload })
                }}
                disabled={!selectedProvider?.available || connectMutation.isPending}
                isLoading={connectMutation.isPending}
                className="gap-1"
              >
                <Plug className="h-4 w-4" /> Connect
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {channelsQuery.isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        </div>
      ) : channels.length === 0 ? (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white py-14 text-center dark:border-neutral-700 dark:bg-neutral-900">
          <Zap className="mx-auto mb-3 h-10 w-10 text-neutral-300" />
          <h3 className="text-base font-semibold text-neutral-800 dark:text-neutral-100">
            No channels connected
          </h3>
          <p className="mt-1 text-sm text-neutral-500">
            Connect your first channel to start receiving customer messages.
          </p>
          <Button className="mt-4" onClick={() => setOpen(true)}>
            {t("connect_channel")}
          </Button>
        </div>
      ) : (
        <div className="grid gap-3">
          {channels.map((channel) => (
            <ChannelCard
              key={channel.id}
              channel={channel}
              label={labelFor(channel.provider)}
              pending={toggleMutation.isPending || disconnectMutation.isPending}
              onToggle={(value) => toggleMutation.mutate(value)}
              onDisconnect={(value) => disconnectMutation.mutate(value)}
            />
          ))}
        </div>
      )}
    </div>
  )
}