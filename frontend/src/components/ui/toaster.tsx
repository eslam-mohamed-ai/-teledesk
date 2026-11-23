import * as React from "react"
import {
  Toast,
  ToastAction,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@radix-ui/react-toast"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

type ToasterProps = {
  className?: string
}

export function Toaster({ className }: ToasterProps) {
  return (
    <ToastProvider>
      <ToastViewport className={cn("fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-4 sm:mr-4", className)} />
    </ToastProvider>
  )
}

type ToastProps = {
  title?: string
  description?: string
  action?: React.ReactNode
  variant?: "default" | "destructive" | "success"
}

let count = 0

function genId() {
  count++
  return `toast-${count}`
}

const toastRoot = (props: ToastProps) => {
  const { title, description, action, variant = "default" } = props
  const id = genId()

  const baseClasses = "flex w-full items-center gap-2 rounded-lg border bg-white p-4 shadow-lg dark:bg-neutral-900 dark:border-neutral-700"
  const variantClasses = {
    default: "border-neutral-200 dark:border-neutral-700",
    destructive: "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/30 dark:text-red-100",
    success: "border-green-200 bg-green-50 text-green-900 dark:border-green-900 dark:bg-green-950/30 dark:text-green-100",
  }

  return (
    <Toast key={id} {...{ id }}>
      <div className={cn(baseClasses, variantClasses[variant])}>
        <div className="grid gap-1 flex-1">
          {title && <ToastTitle className="text-sm font-semibold">{title}</ToastTitle>}
          {description && <ToastDescription className="text-sm opacity-90">{description}</ToastDescription>}
        </div>
        {action && <ToastAction altText="Action">{action}</ToastAction>}
        <ToastClose asChild>
          <button className="rounded p-1 text-neutral-400 hover:text-neutral-600 dark:text-neutral-500 dark:hover:text-neutral-300">
            <X className="h-4 w-4" />
          </button>
        </ToastClose>
      </div>
    </Toast>
  )
}

export function toast(props: ToastProps) {
  const event = new CustomEvent("teledesk-toast", { detail: { component: toastRoot(props) } })
  window.dispatchEvent(event)
}

toast.success = (title: string, description?: string) => toast({ title, description, variant: "success" })
toast.error = (title: string, description?: string) => toast({ title, description, variant: "destructive" })

export function useToast() {
  return { toast }
}