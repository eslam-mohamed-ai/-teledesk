import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { ChannelCard } from "./ChannelCard"
import type { Channel } from "@/types/inbox"

const channel: Channel = {
  id: 7,
  provider: "telegram",
  external_id: "123456",
  display_name: "Support bot",
  status: "connected",
  active: true,
  capabilities: { inbound: true, outbound: true },
}

describe("ChannelCard", () => {
  it("renders the provider label and connection state", () => {
    render(
      <ChannelCard
        channel={channel}
        label="Telegram"
        onToggle={vi.fn()}
        onDisconnect={vi.fn()}
      />,
    )

    expect(screen.getByText(/Telegram/)).toBeInTheDocument()
    expect(screen.getByText("connected")).toBeInTheDocument()
    expect(screen.getByText("Active")).toBeInTheDocument()
  })

  it("calls onToggle when the toggle button is clicked", async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    const onDisconnect = vi.fn()

    render(
      <ChannelCard
        channel={channel}
        label="Telegram"
        onToggle={onToggle}
        onDisconnect={onDisconnect}
      />,
    )

    await user.click(screen.getByRole("button", { name: /deactivate/i }))
    expect(onToggle).toHaveBeenCalledWith(channel)
    expect(onDisconnect).not.toHaveBeenCalled()
  })

  it("calls onDisconnect when disconnect is clicked", async () => {
    const user = userEvent.setup()
    const onDisconnect = vi.fn()

    render(
      <ChannelCard
        channel={channel}
        label="Telegram"
        onToggle={vi.fn()}
        onDisconnect={onDisconnect}
      />,
    )

    await user.click(screen.getByRole("button", { name: /disconnect/i }))
    expect(onDisconnect).toHaveBeenCalledWith(channel)
  })
})