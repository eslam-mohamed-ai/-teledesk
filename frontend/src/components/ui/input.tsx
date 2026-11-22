import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  type?: "text" | "email" | "password" | "number" | "tel" | "url"
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, type = "text", id, ...props }, ref) => {
    const generatedId = React.useId()
    const inputId = id ?? generatedId
    return (
      <div className="w-full space-y-1">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300"
          >
            {label}
          </label>
        )}
        <input
          type={type}
          ref={ref}
          id={inputId}
          className={cn(
            "flex h-10 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm ring-offset-white file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-red-500 focus-visible:ring-red-500",
            className,
          )}
          {...props}
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    )
  },
)
Input.displayName = "Input"
