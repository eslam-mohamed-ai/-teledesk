import * as React from "react"
import { ToastAction, ToastProvider, ToastViewport } from "@radix-ui/react-toast"
import { cn } from "@/lib/utils"
import { x } from "lucide-react"

const TOAST_LIMIT = 1
const TOAST_REMOVE_DELAY = 1000000

type ToasterProps = {
  className?: string
}

export function Toaster({ className }: ToasterProps) {
  return (
    <ToastProvider>
      <ToastViewport className={cn("fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-4 sm:mr-4", className)}>
        <ToastAction />
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
  const el = document.getElementById("teledesk-toast-container")
  // Minimal implementation - dispatch a custom event
  const event = new CustomEvent("teledesk-toast", { detail: { id, title, description, action } })
  window.dispatchEvent(event)
}

export function useToast() {
  return { toast }
}
