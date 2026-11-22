import * as React from "react"
import { cn } from "@/lib/utils"

export const Skeleton = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800",
        className,
      )}
      {...props}
    />
  ),
)
Skeleton.displayName = "Skeleton"

export interface SkeletonTextProps extends React.HTMLAttributes<HTMLDivElement> {
  lines?: number
  lineWidth?: string | number
}

export const SkeletonText = React.forwardRef<HTMLDivElement, SkeletonTextProps>(
  ({ className, lines = 3, lineWidth = "100%", ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-2 w-full", className)} {...props}>
      {[...Array(lines)].map((_, i) => (
        <div key={i} className="h-4 w-full rounded bg-neutral-200 dark:bg-neutral-800 animate-pulse" style={{ width: lineWidth }} />
      ))}
    </div>
  ),
)
SkeletonText.displayName = "SkeletonText"
