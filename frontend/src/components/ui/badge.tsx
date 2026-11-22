import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "brand"
}

const variants = {
  default: "bg-neutral-100 text-neutral-800",
  secondary: "bg-neutral-200 text-neutral-700",
  destructive: "bg-red-500 text-white",
  outline: "border border-neutral-200 text-neutral-700 bg-white",
  brand: "bg-brand-100 text-brand-700",
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-tight",
        variants[variant],
        className,
      )}
      {...props}
    />
  ),
)
Badge.displayName = "Badge"
