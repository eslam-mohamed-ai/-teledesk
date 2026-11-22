import * as React from "react"
import { ToastAction, ToastProvider, ToastViewport } from "@radix-ui/react-toast"
import { cn } from "@/lib/utils"

type ToasterProps = {
  className?: string
}

export function Toaster({ className }: ToasterProps) {
  return (
    <ToastProvider>
      <ToastViewport className={cn("fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-4 sm:mr-4", className)}>
        <ToastAction altText="Dismiss" />
      </ToastViewport>
    </ToastProvider>
  )
}

type ToastProps = {
  title?: string
  description?: string
  action?: React.ReactNode
}

let count = 0
export function toast({ title, description, action }: ToastProps) {
  count++
  const id = `toast-${count}`
  // Minimal implementation - dispatch a custom event
  const event = new CustomEvent("teledesk-toast", { detail: { id, title, description, action } })
  window.dispatchEvent(event)
}

export function useToast() {
  return { toast }
}
