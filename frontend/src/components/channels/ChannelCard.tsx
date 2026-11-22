import * as React from "react"
import { Mail, MessageCircle, Send, Camera, Power, Unplug, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Channel } from "@/types/inbox"

const ICONS: Record<string, React.ElementType> = {
  telegram: Send,
  messenger: MessageCircle,
  whatsapp: MessageCircle,
  instagram: Camera,
}

function ProviderIcon({ provider }: { provider: string }) {
  const Icon = ICONS[provider] || Mail
  return <Icon className="h-5 w-5" />
}

type Props = {
  channel: Channel
  label: string
  onToggle: (channel: Channel) => void
  onDisconnect: (channel: Channel) => void
  pending?: boolean
}

export function ChannelCard({ channel, label, onToggle, onDisconnect, pending }: Props) {
  const status = channel.status || "unknown"
  const connected = channel.active && status === "connected"
  const tone = connected ? "ok" : status === "needs_attention" ? "warn" : "down"

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
              connected
                ? "bg-brand-100 text-brand-700"
                : "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
            )}
          >
            <ProviderIcon provider={channel.provider} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              {channel.display_name || label}
            </p>
            <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">
              {label}
              {channel.external_id ? ` · ${channel.external_id}` : ""}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
              tone === "ok"
                ? "bg-green-50 text-green-700"
                : tone === "warn"
                  ? "bg-amber-50 text-amber-700"
                  : "bg-red-50 text-red-700",
            )}
          >
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                tone === "ok" ? "bg-green-500" : tone === "warn" ? "bg-amber-500" : "bg-red-500",
              )}
            />
            {status}
          </span>
          <Badge variant={channel.active ? "brand" : "outline"}>{channel.active ? "Active" : "Inactive"}</Badge>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1 px-2 text-xs"
            onClick={() => onToggle(channel)}
            disabled={pending}
          >
            {pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Power className="h-3.5 w-3.5" />}
            {channel.active ? "Deactivate" : "Activate"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-8 gap-1 px-2 text-xs text-red-600 hover:bg-red-50"
            onClick={() => onDisconnect(channel)}
            disabled={pending}
          >
            <Unplug className="h-3.5 w-3.5" /> Disconnect
          </Button>
        </div>
      </div>

      {Object.keys(channel.capabilities || {}).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-neutral-100 pt-3 dark:border-neutral-800">
          {Object.entries(channel.capabilities).map(([key, value]) => (
            <span
              key={key}
              className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
            >
              {key}: {String(value)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}