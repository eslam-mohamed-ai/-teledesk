import * as React from "react"
import { cn } from "@/lib/utils"
import { User as LucideUser } from "lucide-react"

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string
  alt?: string
  size?: "sm" | "md" | "lg"
}

const sizes = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-12 w-12",
}

export const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, src, alt, size = "md", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "relative flex shrink-0 overflow-hidden rounded-full",
        sizes[size],
        className,
      )}
      {...props}
    >
      {src ? <img src={src} alt={alt} className="aspect-square h-full w-full object-cover" /> : <LucideUser className="fill-current" />}
    </div>
  ),
)
Avatar.displayName = "Avatar"
