import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart, Bar, LineChart, Line, ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts"
import { Mail, Users, Clock, AlertCircle, Bot } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"

const COLORS = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]

type Metric = { label: string; value: number | string; change: string; icon: React.ElementType; trend: "up" | "down" | "neutral" }
type ConversationStat = { name: string; conversations: number; messages: number }
type ChannelStat = { name: string; value: number }

type StatsOverview = {
  messages: number
  messages_prev: number
  automation: number
  answered_auto: number
  bot_total: number
  new_customers: number
  new_customers_delta: number
  avg_latency: number
  handoffs: number
  open_handoffs: number
  top_questions: { q: string; n: number }[]
  unanswered: { q: string; n: number }[]
  peak: Record<string, number>
  langs: { ar: number; en: number; other: number }
  series: number[]
}

export default function Analytics() {
  const { t } = useTranslation()

  const { data: stats } = useQuery<StatsOverview>({
    queryKey: ["analytics-overview"],
    queryFn: async () => {
      const res = await api.get("/stats/overview")
      return res.data
    },
  })

  const defaultMetrics: Metric[] = [
    { label: t("conversations"), value: 0, change: "+12%", icon: Mail, trend: "up" },
    { label: t("messages"), value: 0, change: "+8%", icon: Bot, trend: "up" },
    { label: t("contacts"), value: 0, change: "+5%", icon: Users, trend: "up" },
    { label: t("avg_response"), value: "2m 34s", change: "-10%", icon: Clock, trend: "down" },
  ]

  const defaultConversationStats: ConversationStat[] = [
    { name: t("mon"), conversations: 4, messages: 12 },
    { name: t("tue"), conversations: 7, messages: 23 },
    { name: t("wed"), conversations: 6, messages: 18 },
    { name: t("thu"), conversations: 9, messages: 31 },
    { name: t("fri"), conversations: 5, messages: 14 },
    { name: t("sat"), conversations: 3, messages: 9 },
    { name: t("sun"), conversations: 2, messages: 6 },
  ]

  const defaultChannelStats: ChannelStat[] = [
    { name: t("telegram"), value: 45 },
    { name: t("messenger"), value: 30 },
    { name: t("whatsapp"), value: 15 },
    { name: t("instagram"), value: 10 },
  ]

  const metrics = React.useMemo<Metric[]>(() => {
    if (!stats) return defaultMetrics
    return [
      { label: t("conversations"), value: stats.new_customers, change: stats.new_customers_delta >= 0 ? `+${stats.new_customers_delta}%` : `${stats.new_customers_delta}%`, icon: Mail, trend: stats.new_customers_delta >= 0 ? "up" : "down" },
      { label: t("messages"), value: stats.messages, change: stats.messages_prev > 0 ? `+${Math.round((stats.messages - stats.messages_prev) / stats.messages_prev * 100)}%` : "+0%", icon: Bot, trend: stats.messages >= stats.messages_prev ? "up" : "down" },
      { label: t("automation"), value: `${stats.automation}%`, change: `${stats.answered_auto} auto`, icon: Bot, trend: stats.automation > 50 ? "up" : "neutral" },
      { label: t("avg_response"), value: `${stats.avg_latency}s`, change: stats.handoffs > 0 ? `${stats.handoffs} handoffs` : t("good"), icon: Clock, trend: stats.handoffs > 5 ? "down" : "up" },
    ]
  }, [stats])

  const conversationStats = React.useMemo<ConversationStat[]>(() => {
    if (!stats || !stats.series.length) return defaultConversationStats
    const days = [t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat"), t("sun")]
    return stats.series.slice(-7).map((value, i) => ({
      name: days[i],
      conversations: value,
      messages: Math.round(value * 2.5),
    }))
  }, [stats])

  const channelStats = React.useMemo<ChannelStat[]>(() => {
    if (!stats) return defaultChannelStats
    return [
      { name: t("telegram"), value: Math.round(stats.messages * 0.6) },
      { name: t("messenger"), value: Math.round(stats.messages * 0.25) },
      { name: t("whatsapp"), value: Math.round(stats.messages * 0.1) },
      { name: t("instagram"), value: Math.round(stats.messages * 0.05) },
    ]
  }, [stats])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{t("analytics")}</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          {t("analytics_overview")}
        </p>
      </div>

      {/* Metrics cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{m.label}</CardTitle>
              <m.icon className="h-4 w-4 text-neutral-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{m.value}</div>
              <div className={cn("text-xs font-medium mt-1", m.trend === "up" ? "text-brand-600" : m.trend === "down" ? "text-destructive" : "text-neutral-500")}>
                {m.change}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("conversations_over_time")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={conversationStats.map((d, i) => ({ ...d, fill: COLORS[i % COLORS.length] }))}>
                  <defs>
                    <linearGradient id="colorConversations" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip />
                  <Line type="monotone" dataKey="conversations" stroke="#8884d8" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("messages_by_channel")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={channelStats}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {channelStats.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                    <Tooltip />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("channel_performance")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channelStats}>
                <Tooltip />
                <Bar dataKey="value" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}