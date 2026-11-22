import * as React from "react"
import { cn } from "@/lib/utils"

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
  header?: React.ReactNode
  footer?: React.ReactNode
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, header, footer, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-lg border border-neutral-200 bg-white shadow-sm dark:border-neutral-700 dark:bg-neutral-900",
        className,
      )}
      {...props}
    >
      {header && <div className="flex flex-col space-y-1.5 p-6">{header}</div>}
      <div className="p-6 pt-0">{children}</div>
      {footer && <div className="flex items-center space-x-2 p-6 pt-0">{footer}</div>}
    </div>
  ),
)
Card.displayName = "Card"

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
  title?: string
  description?: string
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, title, description, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props}>
      {title && <h3 className="text-xl font-semibold">{title}</h3>}
      {description && <p className="text-sm text-neutral-600">{description}</p>}
    </div>
  ),
)
CardHeader.displayName = "CardHeader"

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center space-x-2 p-6 pt-0", className)} {...props} />
  ),
)
CardFooter.displayName = "CardFooter"

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
)
CardContent.displayName = "CardContent"

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-xl font-semibold leading-none tracking-tight", className)} {...props} />
  ),
)
CardTitle.displayName = "CardTitle"

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn("text-sm text-neutral-500 dark:text-neutral-400", className)} {...props} />
))
CardDescription.displayName = "CardDescription"
