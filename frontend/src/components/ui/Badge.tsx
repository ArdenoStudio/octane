import React from "react"

interface BadgeProps extends React.ComponentPropsWithoutRef<"span"> {}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ children, className, ...props }, forwardedRef) => {
    return (
      <span
        ref={forwardedRef}
        className={`z-10 block w-fit rounded-lg border border-amber-200/60 bg-amber-50/70 px-3 py-1.5 text-sm font-semibold uppercase leading-4 tracking-tighter ${className ?? ""}`}
        {...props}
      >
        <span className="bg-gradient-to-b from-amber-500 to-amber-600 bg-clip-text text-transparent">
          {children}
        </span>
      </span>
    )
  },
)

Badge.displayName = "Badge"

export { Badge, type BadgeProps }
