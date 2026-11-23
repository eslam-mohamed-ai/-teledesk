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

type BotConfig = {
  bot: {
    id: number
    name: string
    username: string
    active: boolean
    connected: boolean
    link: string | null
  } | null
  today: number
  customers: number
  last_message: string | null
  log: { flag: string; customer: string; text: string; at: string }[]
}

export default function AI() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: config, isLoading } = useQuery<BotConfig>({
    queryKey: ["bot-config"],
    queryFn: async () => {
      const res = await api.get("/bots")
      return res.data
    },
  })

  const [testMessage, setTestMessage] = React.useState("")
  const [testResult, setTestResult] = React.useState<{ answer: string; source?: string; needs_human: boolean; in_scope: boolean } | null>(null)

  const updateConfigMutation = useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const res = await api.post("/bots/connect", data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bot-config"] })
    },
  })

  const testAssistantMutation = useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post("/bots/test", { question: message })
      return res.data
    },
    onSuccess: (data) => {
      setTestResult(data)
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{t("ai_agent")}</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          {t("ai_agent_configure")}
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("bot_connection")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-10">
                <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
              </div>
            ) : config?.bot ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    {t("bot_name")}
                  </label>
                  <Input value={config.bot.name} disabled />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    {t("username")}
                  </label>
                  <Input value={config.bot.username} disabled />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    id="bot-active"
                    type="checkbox"
                    checked={config.bot.active}
                    onChange={() => {}}
                    className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
                  />
                  <label htmlFor="bot-active" className="text-sm text-neutral-700 dark:text-neutral-300">
                    {t("bot_active")}
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    id="bot-connected"
                    type="checkbox"
                    checked={config.bot.connected}
                    disabled
                    className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500 dark:bg-neutral-800 dark:border-neutral-700"
                  />
                  <label htmlFor="bot-connected" className="text-sm text-neutral-700 dark:text-neutral-300">
                    {t("connected_to_telegram")}
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-brand-600" />
                  <a href={config.bot.link} target="_blank" rel="noopener noreferrer" className="text-sm text-brand-600 hover:underline">
                    {t("open_in_telegram")}
                  </a>
                </div>
                <Button onClick={() => updateConfigMutation.mutate({})} disabled={updateConfigMutation.isPending}>
                  {t("reconnect_bot")}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-neutral-500">{t("no_bot_connected")}</p>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    {t("bot_token")}
                  </label>
                  <Input
                    type="password"
                    placeholder={t("bot_token_placeholder")}
                    onChange={(e) => {}}
                  />
                </div>
                <Button onClick={() => updateConfigMutation.mutate({ token: "" })} disabled={updateConfigMutation.isPending}>
                  {t("connect_bot")}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("test_assistant")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder={t("ask_question")}
                className="flex-1"
              />
              <Button onClick={() => testAssistantMutation.mutate(testMessage)} disabled={testAssistantMutation.isPending || !testMessage.trim()}>
                <Send className="h-4 w-4 mr-1" /> {t("ask")}
              </Button>
            </div>
            {testAssistantMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
                <span>{t("thinking")}</span>
              </div>
            )}
            {testResult && (
              <div className="bg-brand-50 dark:bg-brand-900/20 rounded-lg p-4 border border-brand-100 dark:border-brand-800">
                <div className="flex items-start gap-2 mb-2">
                  <Bot className="h-4 w-4 text-brand-600" />
                  <span className="text-xs font-medium text-brand-700 dark:text-brand-400 uppercase">{t("assistant")}</span>
                </div>
                <p className="text-sm text-neutral-900 dark:text-neutral-100">{testResult.answer}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-neutral-500">
                  <span>{t("source")}: {testResult.source || t("knowledge_base")}</span>
                  <Badge variant={testResult.needs_human ? "destructive" : "secondary"} className="text-[10px]">
                    {testResult.needs_human ? t("needs_human") : t("auto")}
                  </Badge>
                  <Badge variant={testResult.in_scope ? "brand" : "secondary"} className="text-[10px]">
                    {testResult.in_scope ? t("in_scope") : t("out_of_scope")}
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
