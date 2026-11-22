import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { Shell } from "@/components/shell/layout"

vi.mock("@/store/authStore", () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: 1, name: "Test User", email: "test@example.com", role: "owner", email_verified: true },
    company: { id: 1, name: "Test Co", plan: "starter", onboarding_step: null, onboarding_completed_at: null, profile: null, lead_capture_enabled: false, lead_capture_consent_text: "" },
    isAuthenticated: true,
    isLoading: false,
    setAuth: vi.fn(),
    setCompany: vi.fn(),
    updateUser: vi.fn(),
    logout: vi.fn(),
    setLanguage: vi.fn(),
    language: "en",
    bootstrap: vi.fn(),
  })),
}))

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { items: [] } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
  errorMessage: (error: unknown) => String(error),
}))

describe("Shell", () => {
  it("renders", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <Shell>Hello</Shell>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByText("Hello")).toBeInTheDocument()
  })
})