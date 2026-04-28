import { Slot } from "@radix-ui/react-slot"
import { RiLoader2Fill } from "@remixicon/react"
import React from "react"
import { tv, type VariantProps } from "tailwind-variants"
import { cx, focusRing } from "../../lib/utils"

const buttonVariants = tv({
  base: [
    "relative inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-center text-sm font-semibold whitespace-nowrap shadow-xs transition-all duration-100 ease-in-out",
    "disabled:pointer-events-none disabled:shadow-none",
    focusRing,
  ],
  variants: {
    variant: {
      primary: [
        "border-transparent",
        "text-zinc-900",
        "bg-accent hover:bg-amber-400",
        "disabled:bg-amber-200 disabled:text-zinc-500",
      ],
      secondary: [
        "border-ink-700",
        "text-ink-200",
        "bg-transparent",
        "hover:bg-ink-900",
        "disabled:text-ink-600",
      ],
      light: [
        "shadow-none border-transparent",
        "text-ink-200",
        "bg-ink-900 hover:bg-ink-800",
        "disabled:bg-ink-900 disabled:text-ink-600",
      ],
      ghost: [
        "shadow-none border-transparent",
        "text-ink-200",
        "bg-transparent hover:bg-ink-900",
        "disabled:text-ink-600",
      ],
      destructive: [
        "border-transparent text-white",
        "bg-red-600 hover:bg-red-700",
        "disabled:bg-red-300",
      ],
    },
  },
  defaultVariants: {
    variant: "primary",
  },
})

interface ButtonProps
  extends React.ComponentPropsWithoutRef<"button">,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  isLoading?: boolean
  loadingText?: string
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      asChild,
      isLoading = false,
      loadingText,
      className,
      disabled,
      variant,
      children,
      ...props
    },
    forwardedRef,
  ) => {
    const Component = asChild ? Slot : "button"
    return (
      <Component
        ref={forwardedRef}
        className={cx(buttonVariants({ variant }), className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <span className="pointer-events-none flex shrink-0 items-center justify-center gap-1.5">
            <RiLoader2Fill className="size-4 shrink-0 animate-spin" aria-hidden="true" />
            <span className="sr-only">{loadingText ?? "Loading"}</span>
            {loadingText ?? children}
          </span>
        ) : (
          children
        )}
      </Component>
    )
  },
)

Button.displayName = "Button"

export { Button, buttonVariants, type ButtonProps }
