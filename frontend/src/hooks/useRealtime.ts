import * as React from "react"
import { useQueryClient } from "@tanstack/react-query"

type RealtimeEvent = {
  type?: string
  conversation_id?: number
  [key: string]: unknown
}

/**
 * Subscribe to GET /api/realtime (SSE). Cookies authenticate the stream, so no
 * token is passed explicitly. Any event invalidates the inbox queries, which
 * keeps the list/thread/contact panel fresh across tabs and agents.
 */
export function useRealtime(enabled = true, onEvent?: (event: RealtimeEvent) => void) {
  const queryClient = useQueryClient()
  const [connected, setConnected] = React.useState(false)
  const retryRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(() => {
    if (!enabled) return
    let source: EventSource | null = null
    let closed = false

    const connect = () => {
      if (closed) return
      source = new EventSource("/api/realtime", { withCredentials: true })

      source.onopen = () => setConnected(true)
      source.onerror = () => {
        setConnected(false)
        source?.close()
        if (!closed) retryRef.current = setTimeout(connect, 3000)
      }
      source.onmessage = (message) => {
        let event: RealtimeEvent = {}
        try {
          event = JSON.parse(message.data)
        } catch {
          event = { type: "message" }
        }
        setConnected(true)
        queryClient.invalidateQueries({ queryKey: ["conversations"] })
        if (event.conversation_id) {
          queryClient.invalidateQueries({ queryKey: ["messages", event.conversation_id] })
          queryClient.invalidateQueries({ queryKey: ["notes", event.conversation_id] })
        }
        onEvent?.(event)
      }
    }

    connect()
    return () => {
      closed = true
      source?.close()
      if (retryRef.current) clearTimeout(retryRef.current)
    }
  }, [enabled, queryClient, onEvent])

  return { connected }
}