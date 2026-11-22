import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Globe, Users, CreditCard, Shield, Bell, FileText, Settings as SettingsIcon } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"

type TeamMember = {
  id: number
  name: string
  email: string
  role: string
  status: string
}

type Invitation = {
  id: number
  email: string
  role: string
  status: string
  created_at: string
}

export default function Settings() {
  const { t, language, changeLanguage } = useTranslation()
  const queryClient = useQueryClient()

  const [tab, setTab] = React.useState<string>("company")

  const { data: company } = useQuery({
    queryKey: ["company"],
    queryFn: async () => {
      const res = await api.get("/company/settings")
      return res.data
    },
  })

  const updateCompanyMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const res = await api.put("/company/settings", data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company"] })
    },
  })

  const members: TeamMember[] = [
    { id: 1, name: "Alice Johnson", email: "alice@example.com", role: "Admin", status: "Active" },
    { id: 2, name: "Bob Smith", email: "bob@example.com", role: "Agent", status: "Active" },
  ]

  const invitations: Invitation[] = [
    { id: 1, email: "carol@example.com", role: "Agent", status: "Pending", created_at: "2 days ago" },
  ]

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
                value={company?.plan || "Starter"}
                onChange={(e) => {}}
                disabled
              />
              <Input
                label="Lead capture consent text"
                value={company?.lead_capture_consent_text || ""}
                onChange={(e) => {}}
              />
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
            <CardHeader>
              <CardTitle>Team members</CardTitle>
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
                      <Badge variant={m.status === "Active" ? "brand" : "secondary"} className="text-xs">
                        {m.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
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
                    <Badge variant="secondary" className="text-xs">{inv.status}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
            <CardFooter>
              <Button variant="outline" className="w-full">
                Invite member
              </Button>
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}
