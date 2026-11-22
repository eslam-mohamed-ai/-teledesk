import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Check, ChevronRight, Mail, Zap, FileText, Users, Globe } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"

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

export default function Onboarding() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: state } = useQuery<OnboardingState>({
    queryKey: ["onboarding"],
    queryFn: async () => {
      const res = await api.get("/onboarding/state")
      return res.data
    },
  })

  const [currentStepIndex, setCurrentStepIndex] = React.useState(0)
  const [stepData, setStepData] = React.useState<StepData>({})

  const saveStep = useMutation({
    mutationFn: async ({ step, data }: { step: OnboardingStep; data: StepData }) => {
      const res = await api.post("/onboarding/step", { step, data })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding"] })
    },
  })

  const currentStep = STEPS[currentStepIndex]
  const isLastStep = currentStepIndex === STEPS.length - 1
  const stepDone = state?.steps.find((s) => s.step === currentStep.id)?.done || false

  const handleSave = () => {
    saveStep.mutate({ step: currentStep.id, data: stepData })
    if (!isLastStep) {
      setCurrentStepIndex((i) => i + 1)
    }
  }

  const progress = (state?.steps.filter((s) => s.done).length / STEPS.length) * 100

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Onboarding</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Set up your company, AI assistant, and first channel to get started.
        </p>
      </div>

      {/* Progress */}
      <div className="w-full">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-neutral-600">{t("onboarding")}</span>
          <span className="text-neutral-600">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
          <div
            className="h-full bg-brand-600 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Step indicator */}
      <div className="flex gap-1">
        {STEPS.map((step, i) => {
          const done = state?.steps.find((s) => s.step === step.id)?.done || false
          const active = i === currentStepIndex
          return (
            <div
              key={step.id}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                done
                  ? "bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400"
                  : active
                  ? "bg-brand-600 text-white"
                  : "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
              )}
            >
              {done ? (
                <Check className="h-4 w-4" />
              ) : (
                <span className="h-5 w-5">{i + 1}</span>
              )}
              {step.label}
            </div>
          )
        })}
      </div>

      {/* Step content */}
      <Card>
        <CardHeader>
          <CardTitle>{currentStep.label}</CardTitle>
          <CardDescription>
            {currentStep.id === "profile"
              ? "Tell us about your company so we can personalize your experience."
              : currentStep.id === "ai"
              ? "Configure your AI assistant's behavior and tone."
              : currentStep.id === "channel"
              ? "Connect your first messaging channel."
              : currentStep.id === "knowledge"
              ? "Upload documents to train your AI assistant."
              : currentStep.id === "test"
              ? "Test your AI assistant before going live."
              : "Invite team members to collaborate."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {currentStep.id === "profile" && (
            <div className="grid md:grid-cols-2 gap-6">
              <Input label="Company name" defaultValue={stepData.company_name || ""} onChange={(e) => setStepData({ ...stepData, company_name: e.target.value })} />
              <Input label="Website" type="url" defaultValue={stepData.website || ""} onChange={(e) => setStepData({ ...stepData, website: e.target.value })} />
              <Input label="Industry" defaultValue={stepData.industry || ""} onChange={(e) => setStepData({ ...stepData, industry: e.target.value })} />
              <Input label="Country" defaultValue={stepData.country || ""} onChange={(e) => setStepData({ ...stepData, country: e.target.value })} />
            </div>
          )}
          {currentStep.id === "ai" && (
            <div className="grid md:grid-cols-2 gap-6">
              <Input label="Welcome message" defaultValue={stepData.welcome || "Hello! How can I help you today?"} onChange={(e) => setStepData({ ...stepData, welcome: e.target.value })} />
              <Input label="Tone" defaultValue={stepData.tone || "friendly"} onChange={(e) => setStepData({ ...stepData, tone: e.target.value })} />
            </div>
          )}
          {currentStep.id === "channel" && (
            <div className="bg-neutral-50 rounded-lg p-6">
              <p className="text-sm text-neutral-500 mb-4">
                Connect your first channel to receive customer messages. You can also skip this and
                connect later from the Channels page.
              </p>
              <Button variant="outline" onClick={() => {}} className="w-full">
                Connect Telegram
              </Button>
              <Button variant="outline" className="mt-2 w-full">
                Connect Messenger
              </Button>
            </div>
          )}
          {currentStep.id === "knowledge" && (
            <div className="bg-neutral-50 rounded-lg p-6 text-center">
              <FileText className="mx-auto mb-4 h-12 w-12 text-neutral-400" />
              <p className="text-sm text-neutral-500 mb-4">
                Upload PDF, TXT, or DOCX documents to train your AI assistant.
              </p>
              <Button variant="outline" className="w-full">
                Upload documents
              </Button>
            </div>
          )}
          {currentStep.id === "test" && (
            <div className="bg-neutral-50 rounded-lg p-6 text-center">
              <p className="text-sm text-neutral-500 mb-4">
                Test your AI assistant with a sample message before going live.
              </p>
              <Button variant="outline" className="w-full">
                Open test chat
              </Button>
            </div>
          )}
          {currentStep.id === "team" && (
            <div className="bg-neutral-50 rounded-lg p-6 text-center">
              <Users className="mx-auto mb-4 h-12 w-12 text-neutral-400" />
              <p className="text-sm text-neutral-500 mb-4">
                Invite teammates to help manage conversations.
              </p>
              <Button variant="outline" className="w-full">
                Invite teammate
              </Button>
            </div>
          )}
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button variant="outline" disabled={currentStepIndex === 0} onClick={() => setCurrentStepIndex((i) => Math.max(0, i - 1))}>
            Back
          </Button>
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span>Step {currentStepIndex + 1} of {STEPS.length}</span>
          </div>
          <Button onClick={handleSave} disabled={saveStep.isPending} className="ml-2">
            {isLastStep ? "Finish" : "Next"} <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </CardFooter>
      </Card>

      {state?.completed && (
        <Card className="border-green-100 bg-green-50">
          <CardContent className="flex items-start gap-3">
            <Check className="h-5 w-5 text-green-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-green-900">Onboarding complete!</h3>
              <p className="text-sm text-green-700 mt-1">
                Your account is ready. Start receiving conversations.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
