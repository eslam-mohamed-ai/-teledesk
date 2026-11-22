import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Check,
  ChevronRight,
  Globe,
  Zap,
  Mail,
  FileText,
  Users,
  Rocket,
  Upload,
  Send,
  UserPlus,
} from "lucide-react"
import { api, errorMessage } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/store/authStore"
import { cn } from "@/lib/utils"
import type { ProviderMetadata } from "@/types/inbox"

type OnboardingStep = "profile" | "ai" | "channel" | "knowledge" | "test" | "team"

const STEPS: { id: OnboardingStep; label: string; icon: React.ElementType }[] = [
  { id: "profile", label: "Company profile", icon: Globe },
  { id: "ai", label: "AI setup", icon: Zap },
  { id: "channel", label: "Connect channel", icon: Mail },
  { id: "knowledge", label: "Upload knowledge", icon: FileText },
  { id: "test", label: "Test assistant", icon: Check },
  { id: "team", label: "Invite teammates", icon: Users },
]

type StepData = Record<string, any>

type OnboardingState = {
  current_step: OnboardingStep | null
  completed: boolean
  completed_at: string | null
  steps: { step: string; done: boolean; data: StepData }[]
}

type Checklist = {
  items: { key: string; label: string; done: boolean }[]
}

export default function Onboarding() {
  const queryClient = useQueryClient()
  const company = useAuthStore((state) => state.company)
  const [currentStepIndex, setCurrentStepIndex] = React.useState(0)
  const [data, setData] = React.useState<StepData>({})
  const [error, setError] = React.useState("")

  const stateQuery = useQuery<OnboardingState>({
    queryKey: ["onboarding"],
    queryFn: async () => (await api.get("/onboarding/state")).data,
  })

  const checklistQuery = useQuery<Checklist>({
    queryKey: ["onboarding-checklist"],
    queryFn: async () => (await api.get("/onboarding/checklist")).data,
  })

  const providersQuery = useQuery<{ items: ProviderMetadata[] }>({
    queryKey: ["channel-providers"],
    queryFn: async () => (await api.get("/channels/providers")).data,
    staleTime: 5 * 60_000,
  })

  const [provider, setProvider] = React.useState("telegram")
  const [providerPayload, setProviderPayload] = React.useState<Record<string, string>>({})
  const [uploadCount, setUploadCount] = React.useState(0)
  const [question, setQuestion] = React.useState("")
  const [testAnswer, setTestAnswer] = React.useState<string | null>(null)
  const [inviteEmail, setInviteEmail] = React.useState("")
  const [inviteRole, setInviteRole] = React.useState("agent")

  const currentStep = STEPS[currentStepIndex]
  const StepIcon = currentStep.icon
  const isLastStep = currentStepIndex === STEPS.length - 1
  const providers = providersQuery.data?.items ?? []
  const selectedProvider = providers.find((item) => item.id === provider) ?? providers[0]

  const saveStep = useMutation({
    mutationFn: async ({ step, values }: { step: OnboardingStep; values: StepData }) => {
      const res = await api.post("/onboarding/step", { step, data: values })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding"] })
      queryClient.invalidateQueries({ queryKey: ["onboarding-checklist"] })
    },
  })

  const saveCompany = useMutation({
    mutationFn: async (values: StepData) => {
      const res = await api.put("/company", {
        name: values.company_name || company?.name || "My company",
        industry: values.industry || "",
        description: values.description || "",
        welcome: values.welcome || "",
        tone: values.tone || "friendly",
        handoff_keywords: values.handoff_keywords || "",
      })
      return res.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["onboarding-checklist"] }),
  })

  const connectChannel = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/channels/${provider}/connect`, { payload: providerPayload })
      return res.data
    },
  })

  const uploadDocument = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      const res = await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      return res.data
    },
    onSuccess: () => {
      setUploadCount((count) => count + 1)
      queryClient.invalidateQueries({ queryKey: ["onboarding-checklist"] })
    },
  })

  const testBot = useMutation({
    mutationFn: async (value: string) => {
      const res = await api.post("/bots/test", { question: value })
      return res.data as { answer: string; source?: string; needs_human: boolean }
    },
    onSuccess: (result) => setTestAnswer(result.answer),
  })

  const inviteMember = useMutation({
    mutationFn: async () => {
      const res = await api.post("/team/invite", { email: inviteEmail, role: inviteRole })
      return res.data
    },
    onSuccess: () => {
      setInviteEmail("")
      queryClient.invalidateQueries({ queryKey: ["onboarding-checklist"] })
    },
  })

  const handleNext = async () => {
    setError("")
    try {
      if (currentStep.id === "profile") {
        await saveCompany.mutateAsync(data)
      }
      if (currentStep.id === "ai") {
        await saveCompany.mutateAsync(data)
      }
      if (currentStep.id === "channel") {
        await connectChannel.mutateAsync()
        setData((prev) => ({ ...prev, provider }))
      }
      if (currentStep.id === "knowledge" && uploadCount === 0) {
        setError("Upload at least one document to continue.")
        return
      }
      if (currentStep.id === "test" && !testAnswer) {
        setError("Run a test message first.")
        return
      }
      if (currentStep.id === "team" && inviteEmail.trim()) {
        await inviteMember.mutateAsync()
      }

      await saveStep.mutateAsync({ step: currentStep.id, values: data })
      setData({})
      setError("")
      if (!isLastStep) setCurrentStepIndex((index) => index + 1)
    } catch (mutationError) {
      setError(errorMessage(mutationError))
    }
  }

  const progress = stateQuery.data
    ? (stateQuery.data.steps.filter((step) => step.done).length / STEPS.length) * 100
    : 0

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Onboarding</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Set up your company, AI assistant, and first channel to get started.
        </p>
      </div>

      <div className="w-full">
        <div className="mb-2 flex justify-between text-sm">
          <span className="text-neutral-600 dark:text-neutral-300">Progress</span>
          <span className="text-neutral-600 dark:text-neutral-300">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
          <div className="h-full bg-brand-600 transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {STEPS.map((step, index) => {
          const done = stateQuery.data?.steps.find((item) => item.step === step.id)?.done
          const active = index === currentStepIndex
          return (
            <button
              key={step.id}
              onClick={() => setCurrentStepIndex(index)}
              className={cn(
                "flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                done
                  ? "bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300"
                  : active
                    ? "bg-brand-600 text-white"
                    : "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
              )}
            >
              {done ? <Check className="h-3.5 w-3.5" /> : <span>{index + 1}</span>}
              <span className="hidden sm:inline">{step.label}</span>
            </button>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <StepIcon className="h-5 w-5 text-brand-600" />
            {currentStep.label}
          </CardTitle>
          <CardDescription>
            {currentStep.id === "profile"
              ? "Tell us about your company so we can personalize your experience."
              : currentStep.id === "ai"
                ? "Configure your AI assistant's welcome message, tone, and handoff keywords."
                : currentStep.id === "channel"
                  ? "Connect your first messaging channel."
                  : currentStep.id === "knowledge"
                    ? "Upload PDF, TXT, or DOCX documents to train your AI assistant."
                    : currentStep.id === "test"
                      ? "Send a test question to your assistant before going live."
                      : "Invite teammates to collaborate."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {currentStep.id === "profile" && (
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Company name"
                value={data.company_name ?? company?.name ?? ""}
                onChange={(event) => setData((prev) => ({ ...prev, company_name: event.target.value }))}
              />
              <Input
                label="Industry"
                value={data.industry ?? ""}
                onChange={(event) => setData((prev) => ({ ...prev, industry: event.target.value }))}
              />
              <div className="md:col-span-2">
                <Input
                  label="What does your company do?"
                  value={data.description ?? ""}
                  onChange={(event) => setData((prev) => ({ ...prev, description: event.target.value }))}
                />
              </div>
            </div>
          )}

          {currentStep.id === "ai" && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <Input
                  label="Welcome message"
                  value={data.welcome ?? ""}
                  placeholder="Hello! How can I help you today?"
                  onChange={(event) => setData((prev) => ({ ...prev, welcome: event.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  Tone
                </label>
                <select
                  value={data.tone ?? "friendly"}
                  onChange={(event) => setData((prev) => ({ ...prev, tone: event.target.value }))}
                  className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                >
                  <option value="friendly">Friendly</option>
                  <option value="professional">Professional</option>
                  <option value="formal">Formal</option>
                  <option value="casual">Casual</option>
                </select>
              </div>
              <Input
                label="Handoff keywords"
                value={data.handoff_keywords ?? ""}
                placeholder="speak to human, agent"
                onChange={(event) => setData((prev) => ({ ...prev, handoff_keywords: event.target.value }))}
              />
            </div>
          )}

          {currentStep.id === "channel" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {providers.map((item) => (
                  <button
                    key={item.id}
                    disabled={!item.available}
                    onClick={() => {
                      setProvider(item.id)
                      setProviderPayload({})
                    }}
                    className={cn(
                      "rounded-lg border p-2.5 text-left text-sm",
                      provider === item.id
                        ? "border-brand-600 bg-brand-50 dark:bg-brand-950/30"
                        : "border-neutral-200 dark:border-neutral-700",
                      !item.available && "cursor-not-allowed opacity-50",
                    )}
                  >
                    <span className="font-medium">{item.label}</span>
                    {!item.available && (
                      <span className="mt-0.5 block text-[10px] text-neutral-400">Coming soon</span>
                    )}
                  </button>
                ))}
              </div>
              {selectedProvider?.available && (
                <div className="space-y-2">
                  {selectedProvider.fields.map((field) => (
                    <Input
                      key={field.key}
                      label={field.label}
                      type={field.type === "password" ? "password" : "text"}
                      value={providerPayload[field.key] || ""}
                      onChange={(event) =>
                        setProviderPayload((prev) => ({ ...prev, [field.key]: event.target.value }))
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {currentStep.id === "knowledge" && (
            <div className="rounded-xl border border-dashed border-neutral-300 p-6 text-center dark:border-neutral-700">
              <Upload className="mx-auto mb-2 h-8 w-8 text-neutral-400" />
              <p className="mb-3 text-sm text-neutral-500">
                Upload PDF, TXT, or DOCX files.
              </p>
              <input
                type="file"
                accept=".pdf,.txt,.docx,.md"
                className="hidden"
                id="onboarding-upload"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) uploadDocument.mutate(file)
                }}
              />
              <Button
                variant="outline"
                onClick={() => document.getElementById("onboarding-upload")?.click()}
              >
                Choose file
              </Button>
              {uploadDocument.isPending && <p className="mt-2 text-xs text-neutral-500">Uploading…</p>}
              {uploadCount > 0 && (
                <Badge variant="brand" className="mt-3">
                  {uploadCount} document{uploadCount > 1 ? "s" : ""} uploaded
                </Badge>
              )}
            </div>
          )}

          {currentStep.id === "test" && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <Input
                  placeholder="Ask your assistant something…"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && question.trim()) testBot.mutate(question.trim())
                  }}
                />
                <Button
                  onClick={() => testBot.mutate(question.trim())}
                  disabled={!question.trim() || testBot.isPending}
                  className="gap-1"
                >
                  <Send className="h-4 w-4" /> Test
                </Button>
              </div>
              {testAnswer && (
                <div className="rounded-lg bg-brand-50 p-3 text-sm text-brand-900 dark:bg-brand-950/30 dark:text-brand-100">
                  {testAnswer}
                </div>
              )}
            </div>
          )}

          {currentStep.id === "team" && (
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                type="email"
                placeholder="teammate@example.com"
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
              />
              <select
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value)}
                className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
              >
                <option value="agent">Agent</option>
                <option value="admin">Admin</option>
              </select>
              <Button
                variant="outline"
                className="gap-1"
                disabled={!inviteEmail.trim() || inviteMember.isPending}
                onClick={() => inviteMember.mutate()}
              >
                <UserPlus className="h-4 w-4" /> Invite
              </Button>
            </div>
          )}

          {error && <p className="text-xs text-red-600">{error}</p>}
          {(saveStep.isError || saveCompany.isError) && (
            <p className="text-xs text-red-600">{errorMessage(saveStep.error || saveCompany.error)}</p>
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button
            variant="outline"
            disabled={currentStepIndex === 0}
            onClick={() => setCurrentStepIndex((index) => Math.max(0, index - 1))}
          >
            Back
          </Button>
          <div className="flex items-center gap-3">
            <span className="text-xs text-neutral-500">
              Step {currentStepIndex + 1} of {STEPS.length}
            </span>
            <Button onClick={handleNext} disabled={saveStep.isPending} className="gap-1">
              {isLastStep ? "Finish" : "Next"} <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Rocket className="h-5 w-5 text-brand-600" /> Getting started
          </CardTitle>
          <CardDescription>Your setup checklist.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {(checklistQuery.data?.items ?? []).map((item) => (
              <li key={item.key} className="flex items-center gap-2 text-sm">
                <span
                  className={cn(
                    "flex h-5 w-5 items-center justify-center rounded-full",
                    item.done
                      ? "bg-brand-600 text-white"
                      : "border border-neutral-300 text-neutral-400 dark:border-neutral-600",
                  )}
                >
                  {item.done && <Check className="h-3 w-3" />}
                </span>
                <span className={item.done ? "text-neutral-500 line-through" : "text-neutral-700 dark:text-neutral-200"}>
                  {item.label}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}