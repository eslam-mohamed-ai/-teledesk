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

export default function Analytics() {
  const { t } = useTranslation()

  const { data: metrics } = useQuery<Metric[]>({
    queryKey: ["analytics-metrics"],
    queryFn: async () => {
      const res = await api.get("/analytics/metrics")
      return res.data.items
    },
  })

  const { data: conversationStats } = useQuery<ConversationStat[]>({
    queryKey: ["analytics-conversations"],
    queryFn: async () => {
      const res = await api.get("/analytics/conversations")
      return res.data.items
    },
  })

  const { data: channelStats } = useQuery<ChannelStat[]>({
    queryKey: ["analytics-channels"],
    queryFn: async () => {
      const res = await api.get("/analytics/channels")
      return res.data.items
    },
  })

  const defaultMetrics: Metric[] = [
    { label: "Conversations", value: 0, change: "+12%", icon: Mail, trend: "up" },
    { label: "Messages", value: 0, change: "+8%", icon: Bot, trend: "up" },
    { label: "Contacts", value: 0, change: "+5%", icon: Users, trend: "up" },
    { label: "Avg response", value: "2m 34s", change: "-10%", icon: Clock, trend: "down" },
  ]

  const defaultConversationStats: ConversationStat[] = [
    { name: "Mon", conversations: 4, messages: 12 },
    { name: "Tue", conversations: 7, messages: 23 },
    { name: "Wed", conversations: 6, messages: 18 },
    { name: "Thu", conversations: 9, messages: 31 },
    { name: "Fri", conversations: 5, messages: 14 },
    { name: "Sat", conversations: 3, messages: 9 },
    { name: "Sun", conversations: 2, messages: 6 },
  ]

  const defaultChannelStats: ChannelStat[] = [
    { name: "Telegram", value: 45 },
    { name: "Messenger", value: 30 },
    { name: "WhatsApp", value: 15 },
    { name: "Instagram", value: 10 },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Analytics</h1>
        <p className="text-neutral-500 dark:text-neutral-400">
          Overview of conversations, messages, and channel performance.
        </p>
      </div>

      {/* Metrics cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {(metrics || defaultMetrics).map((m, i) => (
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
            <CardTitle>Conversations over time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={(conversationStats || defaultConversationStats).map((d, i) => ({ ...d, fill: COLORS[i % COLORS.length] }))}>
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
            <CardTitle>Messages by channel</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={(channelStats || defaultChannelStats)}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {(channelStats || defaultChannelStats).map((entry, index) => (
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
          <CardTitle>Channel performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={(channelStats || defaultChannelStats)}>
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
