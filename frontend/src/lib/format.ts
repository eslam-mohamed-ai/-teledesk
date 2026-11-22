export function dayKey(iso: string | null | undefined): string {
  if (!iso) return "unknown"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "unknown"
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

export function dayLabel(iso: string | null | undefined): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  if (dayKey(iso) === dayKey(today.toISOString())) return "Today"
  if (dayKey(iso) === dayKey(yesterday.toISOString())) return "Yesterday"
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const seconds = Math.round((Date.now() - d.getTime()) / 1000)
  if (seconds < 60) return "now"
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d`
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

export function initials(name: string | null | undefined): string {
  const value = (name || "?").trim()
  if (!value) return "?"
  return value
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("")
}

export function providerLabel(provider: string | null | undefined): string {
  if (!provider) return "Channel"
  return provider.charAt(0).toUpperCase() + provider.slice(1)
}

export function statusLabel(status: string | null | undefined): string {
  switch (status) {
    case "bot":
      return "AI"
    case "needs_human":
      return "Needs human"
    case "human":
      return "Human"
    case "closed":
      return "Closed"
    case "open":
      return "Open"
    default:
      return status || "Unknown"
  }
}