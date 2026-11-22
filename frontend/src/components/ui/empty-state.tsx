import * as React from "react"
import { cn } from "@/lib/utils"
import { Inbox as InboxIcon, Mail as MailIcon, Users as UsersIcon } from "lucide-react"

const icons: Record<string, React.ElementType> = {
  inbox: InboxIcon,
  mail: MailIcon,
  users: UsersIcon,
}

interface EmptyStateProps {
  icon?: keyof typeof icons
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: IconName, title, description, action, className }: EmptyStateProps) {
  const Icon = IconName ? icons[IconName] : null
  return (
    <div className={cn("flex flex-col items-center justify-center text-center p-12", className)}>
      {Icon && <Icon className="mb-4 h-12 w-12 text-neutral-400" />}
      <h3 className="mb-2 text-lg font-semibold text-neutral-900">{title}</h3>
      {description && <p className="mb-6 text-sm text-neutral-500 max-w-sm">{description}</p>}
      {action}
    </div>
  )
}
