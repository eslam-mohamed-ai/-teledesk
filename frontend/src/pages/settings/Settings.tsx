import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Globe, Users, CreditCard, Shield, Bell, FileText, Settings as SettingsIcon, Plus } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"
import type { Member } from "@/types/inbox"

type InviteOut = {
  id: number
  email: string
  role: string
  status: string
  expires_at: string
}

export default function Settings() {
  const { t, language, changeLanguage } = useTranslation()
  const queryClient = useQueryClient()

  const [tab, setTab] = React.useState<string>("company")
  const inviteEmailRef = React.useRef<HTMLInputElement>(null)
  const inviteRoleRef = React.useRef<string>("agent")

  const { data: company } = useQuery({
    queryKey: ["company"],
    queryFn: async () => {
      const res = await api.get("/company")
      return res.data
    },
  })

  const { data: members = [] } = useQuery<Member[]>({
    queryKey: ["team-members"],
    queryFn: async () => (await api.get("/team/members")).data,
  })

  const { data: invitations = [] } = useQuery<InviteOut[]>({
    queryKey: ["team-invitations"],
    queryFn: async () => (await api.get("/team/invitations")).data,
  })

  const updateCompanyMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const res = await api.put("/company", data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company"] })
    },
  })

  const inviteMutation = useMutation({
    mutationFn: async (data: { email: string; role: string }) => {
      const res = await api.post("/team/invite", data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team-invitations"] })
    },
  })

  const revokeInvitationMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/team/invitations/${id}`)
      return id
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team-invitations"] })
    },
  })

  const changeRoleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: number; role: string }) => {
      const res = await api.patch(`/team/members/${userId}/role`, { role })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team-members"] })
    },
  })

  const removeMemberMutation = useMutation({
    mutationFn: async (userId: number) => {
      await api.delete(`/team/members/${userId}`)
      return userId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team-members"] })
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Settings</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Manage your company, team, and preferences.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        {[
          { id: "company", label: "Company settings", icon: SettingsIcon },
          { id: "team", label: "Team & roles", icon: Users },
          { id: "security", label: "Security", icon: Shield },
          { id: "notifications", label: "Notifications", icon: Bell },
          { id: "billing", label: "Billing & usage", icon: CreditCard },
          { id: "language", label: "Language & appearance", icon: Globe },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors",
              tab === item.id
                ? "bg-brand-50 border-brand-200 text-brand-700 dark:bg-brand-900/30 dark:border-brand-500 dark:text-brand-400"
                : "bg-white dark:bg-neutral-800 border-neutral-200 text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700",
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </div>

      {tab === "company" && (
        <Card>
          <CardHeader>
            <CardTitle>Company settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-6">
              <Input
                label="Company name"
                value={company?.name || ""}
                onChange={(e) => {}}
              />
              <Input
                label="Plan"
                value={company?.plan || "free"}
                onChange={(e) => {}}
                disabled
              />
              <Input
                label="Industry"
                value={company?.industry || ""}
                onChange={(e) => {}}
              />
              <Input
                label="Description"
                value={company?.description || ""}
                onChange={(e) => {}}
              />
              <div className="md:col-span-2">
                <Input
                  label="Welcome message"
                  value={company?.welcome || ""}
                  onChange={(e) => {}}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  Tone
                </label>
                <select
                  value={company?.tone || "friendly"}
                  onChange={(e) => {}}
                  className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                >
                  <option value="friendly">Friendly</option>
                  <option value="professional">Professional</option>
                  <option value="formal">Formal</option>
                  <option value="casual">Casual</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  Reply language
                </label>
                <select
                  value={company?.reply_language || "auto"}
                  onChange={(e) => {}}
                  className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                >
                  <option value="auto">Auto</option>
                  <option value="ar">Arabic</option>
                  <option value="en">English</option>
                </select>
              </div>
              <Input
                label="Handoff keywords"
                value={company?.handoff_keywords || ""}
                onChange={(e) => {}}
                placeholder="speak to human, agent"
              />
              <div className="md:col-span-2">
                <Input
                  label="Lead capture consent text"
                  value={company?.lead_capture_consent_text || ""}
                  onChange={(e) => {}}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="lead-capture-enabled"
                type="checkbox"
                checked={company?.lead_capture_enabled ?? false}
                onChange={(e) => {}}
                className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
              />
              <label htmlFor="lead-capture-enabled" className="text-sm text-neutral-700 dark:text-neutral-300">
                Enable lead capture widget
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="handoff-on-request"
                type="checkbox"
                checked={company?.handoff_on_request ?? true}
                onChange={(e) => {}}
                className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
              />
              <label htmlFor="handoff-on-request" className="text-sm text-neutral-700 dark:text-neutral-300">
                Handoff on request
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="handoff-out-of-scope"
                type="checkbox"
                checked={company?.handoff_out_of_scope ?? true}
                onChange={(e) => {}}
                className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
              />
              <label htmlFor="handoff-out-of-scope" className="text-sm text-neutral-700 dark:text-neutral-300">
                Handoff out of scope
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="handoff-after-two"
                type="checkbox"
                checked={company?.handoff_after_two ?? false}
                onChange={(e) => {}}
                className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
              />
              <label htmlFor="handoff-after-two" className="text-sm text-neutral-700 dark:text-neutral-300">
                Handoff after two messages
              </label>
            </div>
            <Input
              label="Work hours (JSON)"
              value={company?.work_hours || ""}
              onChange={(e) => {}}
              placeholder='{"mon": {"open": "09:00", "close": "17:00"}}'
            />
          </CardContent>
          <CardFooter>
            <Button onClick={() => updateCompanyMutation.mutate({})} disabled={updateCompanyMutation.isPending}>
              Save changes
            </Button>
          </CardFooter>
        </Card>
      )}

      {tab === "team" && (
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Team members</CardTitle>
              <Button variant="outline" size="sm" onClick={() => {}}>
                <Plus className="h-4 w-4 mr-1" /> Invite
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-600">
                        <Users className="h-4 w-4" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{m.name}</p>
                        <p className="text-xs text-neutral-500">{m.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">{m.role}</Badge>
                      <Badge variant={m.email_verified ? "brand" : "secondary"} className="text-xs">
                        {m.email_verified ? "Verified" : "Pending"}
                      </Badge>
                    </div>
                  </div>
                ))}
                {members.length === 0 && (
                  <p className="text-sm text-neutral-500 text-center py-4">No team members yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Pending invitations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {invitations.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                    <div>
                      <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{inv.email}</p>
                      <p className="text-xs text-neutral-500">{inv.role} • {inv.status}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">{inv.status}</Badge>
                      <Button variant="ghost" size="sm" onClick={() => revokeInvitationMutation.mutate(inv.id)}>
                        Revoke
                      </Button>
                    </div>
                  </div>
                ))}
                {invitations.length === 0 && (
                  <p className="text-sm text-neutral-500 text-center py-4">No pending invitations.</p>
                )}
              </div>
            </CardContent>
            <CardFooter>
              <div className="flex flex-col gap-2 sm:flex-row w-full">
                <Input
                  type="email"
                  placeholder="teammate@example.com"
                  ref={(el) => { inviteEmailRef.current = el }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.currentTarget.value.trim()) {
                      inviteMutation.mutate({ email: e.currentTarget.value.trim(), role: inviteRoleRef.current })
                      e.currentTarget.value = ""
                    }
                  }}
                />
                <select
                  ref={(el) => { if (el) inviteRoleRef.current = el.value }}
                  defaultValue="agent"
                  className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                >
                  <option value="agent">Agent</option>
                  <option value="admin">Admin</option>
                </select>
                <Button
                  variant="outline"
                  className="gap-1"
                  disabled={inviteMutation.isPending || !inviteEmailRef.current?.value?.trim()}
                  onClick={() => {
                    if (inviteEmailRef.current?.value?.trim() && inviteRoleRef.current) {
                      inviteMutation.mutate({ email: inviteEmailRef.current.value.trim(), role: inviteRoleRef.current })
                      if (inviteEmailRef.current) inviteEmailRef.current.value = ""
                    }
                  }}
                >
                  <Plus className="h-4 w-4" /> Invite
                </Button>
              </div>
            </CardFooter>
          </Card>
        </div>
      )}

      {tab === "language" && (
        <Card>
          <CardHeader>
            <CardTitle>Language & appearance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Language</p>
                <p className="text-xs text-neutral-500">Interface language and text direction.</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => changeLanguage("en")}
                  className={cn("px-3 py-1 rounded text-sm font-medium transition-colors", language === "en" ? "bg-brand-600 text-white" : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}
                >
                  English
                </button>
                <button
                  onClick={() => changeLanguage("ar")}
                  className={cn("px-3 py-1 rounded text-sm font-medium transition-colors", language === "ar" ? "bg-brand-600 text-white" : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}
                >
                  العربية
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Theme</p>
                <p className="text-xs text-neutral-500">Light or dark mode.</p>
              </div>
              <div className="flex gap-2">
                <button className={cn("px-3 py-1 rounded text-sm font-medium transition-colors", "bg-brand-600 text-white")}>
                  Light
                </button>
                <button className={cn("px-3 py-1 rounded text-sm font-medium transition-colors", "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}>
                  Dark
                </button>
                <button className={cn("px-3 py-1 rounded text-sm font-medium transition-colors", "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}>
                  System
                </button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {tab === "security" && (
        <Card>
          <CardHeader>
            <CardTitle>Security</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Security settings such as password policy and session management come here.
            </p>
            <Button variant="outline" className="w-full">
              Manage sessions
            </Button>
          </CardContent>
        </Card>
      )}

      {tab === "notifications" && (
        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Email and push notification preferences come here.
            </p>
          </CardContent>
        </Card>
      )}

      {tab === "billing" && (
        <Card>
          <CardHeader>
            <CardTitle>Billing & usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Subscription plan, invoices, and usage metrics come here.
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                <p className="text-xs text-neutral-500 uppercase font-medium mb-1">Plan</p>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{company?.plan || "free"}</p>
              </div>
              <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                <p className="text-xs text-neutral-500 uppercase font-medium mb-1">Usage</p>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Check limits in dashboard</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}