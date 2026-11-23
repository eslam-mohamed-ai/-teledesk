import { expect, test, type Page } from "@playwright/test"

type MockState = { authed: boolean }

const user = {
  id: 1,
  name: "Ada Lovelace",
  email: "ada@example.com",
  role: "owner",
  email_verified: true,
}

const company = {
  id: 1,
  name: "Analytical Engines Ltd",
  plan: "free",
  onboarding_step: "profile",
  onboarding_completed_at: null,
  profile: {},
  lead_capture_enabled: false,
  lead_capture_consent_text: "",
}

const conversation = {
  id: 1,
  channel_id: 1,
  provider: "telegram",
  channel_provider: "telegram",
  contact_id: 1,
  contact_name: "Jane Doe",
  assignee_user_id: null,
  assignee_name: null,
  status: "open",
  priority: "normal",
  unread_count: 0,
  last_preview: "Hello from customer",
  last_message_at: new Date().toISOString(),
  last_inbound_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  ai_handling: true,
  needs_human: false,
  window_open: true,
  window_expires_at: null,
}

async function mockApi(page: Page, state: MockState) {
  await page.route("**/api/**", async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (path.endsWith("/realtime")) {
      await route.abort()
      return
    }

    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      })

    if (path === "/api/auth/me") {
      return state.authed ? json(user) : json({ detail: "Unauthorized" }, 401)
    }
    if (path === "/api/auth/register") {
      return json({ user, requires_verification: true }, 201)
    }
    if (path === "/api/auth/verify-email") return json({ ok: true, email_verified: true })
    if (path === "/api/auth/login") {
      state.authed = true
      return json({ user, email_verified: true })
    }
    if (path === "/api/auth/refresh") return json({ user })
    if (path === "/api/company") return json(company)

    if (path === "/api/onboarding/state") {
      return json({ current_step: "profile", completed: false, completed_at: null, steps: [] })
    }
    if (path === "/api/onboarding/checklist") return json({ items: [] })
    if (path === "/api/onboarding/step") return json({ step: "profile", done: true, data: {} })

    if (path === "/api/channels/providers") {
      return json({
        items: [
          {
            id: "telegram",
            label: "Telegram",
            available: true,
            coming_soon: false,
            description: "Connect a Telegram bot token.",
            fields: [{ key: "bot_token", label: "Bot token", type: "password", required: true }],
          },
          {
            id: "whatsapp",
            label: "WhatsApp",
            available: false,
            coming_soon: true,
            description: "Coming soon.",
            fields: [],
          },
        ],
      })
    }
    if (path === "/api/channels" || path === "/api/channels/") return json({ items: [] })
    if (/^\/api\/channels\/[^/]+\/connect$/.test(path) && method === "POST") {
      return json({ channel: { id: 1, provider: "telegram", status: "connected", active: true } }, 201)
    }

    if (path === "/api/conversations/" || path === "/api/conversations") {
      return json({ items: [conversation], has_more: false, next_cursor: null })
    }
    if (/^\/api\/conversations\/\d+\/messages$/.test(path)) {
      return json({
        items: [
          {
            id: 1,
            role: "customer",
            direction: "inbound",
            sender_type: "contact",
            content: "Hello from customer",
            content_type: "text",
            delivery_status: null,
            error_code: null,
            created_at: new Date().toISOString(),
          },
        ],
        has_more: false,
        next_cursor: null,
      })
    }
    if (/^\/api\/conversations\/\d+\/notes$/.test(path)) return json({ items: [] })
    if (path === "/api/conversations/canned-replies") return json({ items: [] })
    if (path === "/api/team/members") return json([])

    if (path === "/api/documents/upload") {
      return json({ id: 1, filename: "guide.txt", status: "processing" })
    }
    if (path === "/api/bots/test") {
      return json({ answer: "Hello! How can I help?", needs_human: false, in_scope: true })
    }
    if (path === "/api/team/invite") {
      return json({ id: 1, email: "teammate@example.com", role: "agent" }, 201)
    }

    return json({})
  })
}

test("signup -> onboarding -> connect mocked channel -> inbox", async ({ page }) => {
  const state: MockState = { authed: false }
  await mockApi(page, state)

  // 1. Sign up
  await page.goto("/auth/signup")
  await page.getByLabel("Name").fill("Ada Lovelace")
  await page.getByLabel("Email").fill("ada@example.com")
  await page.getByLabel("Password").fill("password123")
  await page.getByRole("button", { name: /create account/i }).click()
  await expect(page).toHaveURL(/verify-email/)

  // 2. Verify email (mocked) then sign in
  await page.getByRole("button", { name: /i verified my email/i }).click()
  await expect(page).toHaveURL(/auth\/login/)

  await page.getByLabel("Email").fill("ada@example.com")
  await page.getByLabel("Password").fill("password123")
  await page.getByRole("button", { name: /^sign in$/i }).click()
  await expect(page).toHaveURL(/inbox/)

  // 3. Onboarding: company profile -> AI -> connect channel
  await page.goto("/onboarding")
  await expect(page.getByText("Company profile")).toBeVisible()
  await page.getByLabel("Company name").fill("Analytical Engines Ltd")
  await page.getByRole("button", { name: /^next$/i }).click()

  await expect(page.getByText("AI setup")).toBeVisible()
  await page.getByRole("button", { name: /^next$/i }).click()

  await expect(page.getByText("Connect channel")).toBeVisible()
  await page.getByLabel("Bot token").fill("123456:ABC-DEF")
  await page.getByRole("button", { name: /^next$/i }).click()

  // 4. Knowledge upload (mocked)
  await expect(page.getByText("Upload knowledge")).toBeVisible()
  await page.locator("#onboarding-upload").setInputFiles({
    name: "guide.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("hello world"),
  })
  await expect(page.getByText(/1 document uploaded/i)).toBeVisible()
  await page.getByRole("button", { name: /^next$/i }).click()

  // 5. Test chat (mocked)
  await expect(page.getByText("Test assistant")).toBeVisible()
  await page.getByPlaceholder(/ask your assistant/i).fill("What are your hours?")
  await page.getByRole("button", { name: /^test$/i }).click()
  await expect(page.getByText("Hello! How can I help?")).toBeVisible()
  await page.getByRole("button", { name: /^next$/i }).click()

  // 6. Invite teammates (mocked) and finish
  await expect(page.getByText("Invite teammates")).toBeVisible()
  await page.getByPlaceholder("teammate@example.com").fill("grace@example.com")
  await page.getByRole("button", { name: "Invite", exact: true }).click()
  await page.getByRole("button", { name: /finish/i }).click()

  // 7. Inbox: conversation list + message thread
  await page.goto("/inbox")
  await expect(page.getByText("Jane Doe")).toBeVisible()
  await page.getByRole("button", { name: /Jane Doe/ }).click()
  // Scope to message thread bubble to avoid matching conversation list preview
  await expect(page.locator('p.whitespace-pre-wrap').getByText("Hello from customer")).toBeVisible()
})