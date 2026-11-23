import * as React from "react"
import { ToastProvider, ToastViewport } from "@radix-ui/react-toast"
import { cn } from "@/lib/utils"

export function ToastListener() {
  const [toasts, setToasts] = React.useState<React.ReactNode[]>([])

  React.useEffect(() => {
    const handler = (event: CustomEvent) => {
      if (event.detail?.component) {
        setToasts((prev) => [...prev, event.detail.component])
      }
    }
    window.addEventListener("teledesk-toast", handler as EventListener)
    return () => window.removeEventListener("teledesk-toast", handler as EventListener)
  }, [])

  const removeToast = (index: number) => {
    setToasts((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <ToastProvider>
      <ToastViewport className={cn("fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-4 sm:mr-4")}>
        {toasts.map((toast, index) =>
          React.cloneElement(toast as React.ReactElement<any>, {
            onOpenChange: (open: boolean) => {
              if (!open) removeToast(index)
            },
          })
        )}
      </ToastViewport>
    </ToastProvider>
  )
}