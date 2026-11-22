import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Zap, Send, Bot, MessageSquare, Check } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"

export default function AI() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: config, isLoading } = useQuery({
    queryKey: ["ai-config"],
    queryFn: async () => {
      const res = await api.get("/ai/config")
      return res.data
    },
  })

  const [testMessage, setTestMessage] = React.useState("")
  const [testResult, setTestResult] = React.useState<{ response: string; source: string } | null>(null)

  const updateConfigMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const res = await api.post("/ai/config", data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-config"] })
    },
  })

  const testAssistantMutation = useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post("/ai/test", { message })
      return res.data
    },
    onSuccess: (data) => {
      setTestResult(data)
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">AI Agent</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Configure your AI assistant's behavior and test responses.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>AI configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-10">
                <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Welcome message
                  </label>
                  <Input
                    value={config?.welcome_message || ""}
                    onChange={(e) => {}}
                    placeholder="Hello! How can I help you today?"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Tone
                  </label>
                  <Input value={config?.tone || "friendly"} onChange={(e) => {}} placeholder="friendly" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    System prompt
                  </label>
                  <textarea
                    className="w-full min-h-[100px] rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600 dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100 dark:focus:ring-brand-500"
                    placeholder="You are a helpful assistant..."
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    id="ai-enabled"
                    type="checkbox"
                    className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
                  />
                  <label htmlFor="ai-enabled" className="text-sm text-neutral-700 dark:text-neutral-300">
                    AI auto-reply enabled
                  </label>
                </div>
                <Button onClick={() => updateConfigMutation.mutate({})} disabled={updateConfigMutation.isPending}>
                  Save configuration
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Test assistant</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="Ask a question..."
                className="flex-1"
              />
              <Button onClick={() => testAssistantMutation.mutate(testMessage)} disabled={testAssistantMutation.isPending || !testMessage.trim()}>
                <Send className="h-4 w-4 mr-1" /> Ask
              </Button>
            </div>
            {testAssistantMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
                <span>Thinking...</span>
              </div>
            )}
            {testResult && (
              <div className="bg-brand-50 dark:bg-brand-900/20 rounded-lg p-4 border border-brand-100 dark:border-brand-800">
                <div className="flex items-start gap-2 mb-2">
                  <Bot className="h-4 w-4 text-brand-600" />
                  <span className="text-xs font-medium text-brand-700 dark:text-brand-400 uppercase">Assistant</span>
                </div>
                <p className="text-sm text-neutral-900 dark:text-neutral-100">{testResult.response}</p>
                <p className="text-xs text-neutral-500 mt-1">Source: {testResult.source}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
