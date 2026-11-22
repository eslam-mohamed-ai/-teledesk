import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { Shell } from "@/components/shell/layout"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/store/authStore", () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: 1, name: "Test User", email: "test@example.com", role: "owner", email_verified: true },
    company: { id: 1, name: "Test Co", plan: "starter", onboarding_step: null, onboarding_completed_at: null, profile: null, lead_capture_enabled: false, lead_capture_consent_text: "" },
    token: "test-token",
    isAuthenticated: true,
    isLoading: false,
    setAuth: vi.fn(),
    setCompany: vi.fn(),
    updateUser: vi.fn(),
    logout: vi.fn(),
    setLanguage: vi.fn(),
    language: "en",
  })),
}))

describe("Shell", () => {
  it("renders", () => {
    render(
      <MemoryRouter>
        <Shell>Hello</Shell>
      </MemoryRouter>,
    )
    expect(screen.getByText("Hello")).toBeInTheDocument()
  })
})
