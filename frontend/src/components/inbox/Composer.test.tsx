import * as React from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { Composer } from "./Composer"
import type { Conversation } from "@/types/inbox"

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { items: [] } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
  errorMessage: (error: unknown) => String(error),
}))

import { api } from "@/lib/api"

const conversation: Conversation = {
  id: 1,
  channel_id: 1,
  provider: "telegram",
  channel_provider: "telegram",
  contact_id: 1,
  contact_name: "Jane",
  assignee_user_id: null,
  assignee_name: null,
  status: "open",
  priority: "normal",
  unread_count: 0,
  last_preview: null,
  last_message_at: null,
  last_inbound_at: null,
  created_at: null,
  ai_handling: true,
  needs_human: false,
  window_open: true,
  window_expires_at: null,
}

function renderComposer(overrides: Partial<Conversation> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return render(<Composer conversation={{ ...conversation, ...overrides }} />, { wrapper })
}

describe("Composer", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("disables send until there is text", () => {
    renderComposer()
    expect(screen.getByPlaceholderText(/type a message/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled()
  })

  it("sends a reply optimistically via POST /reply", async () => {
    const user = userEvent.setup()
    renderComposer()

    const textarea = screen.getByPlaceholderText(/type a message/i)
    await user.type(textarea, "hello there")

    await user.click(screen.getByRole("button", { name: /send/i }))

    expect(api.post).toHaveBeenCalledWith("/conversations/1/reply", { text: "hello there" })
  })

  it("posts an internal note when the note toggle is on", async () => {
    const user = userEvent.setup()
    renderComposer()

    await user.click(screen.getByTitle("Internal note"))
    await user.type(screen.getByPlaceholderText(/internal note/i), "only for the team")

    await user.click(screen.getByRole("button", { name: /add note/i }))

    expect(api.post).toHaveBeenCalledWith("/conversations/1/note", { note: "only for the team" })
  })

  it("blocks sending when the messaging window is closed", () => {
    renderComposer({ window_open: false })
    expect(screen.getByText(/messaging window closed/i)).toBeInTheDocument()
  })
})