import { RiEyeFill, RiEyeOffFill, RiSearchLine } from "@remixicon/react"
import React from "react"
import { tv, type VariantProps } from "tailwind-variants"
import { cx, focusInput, hasErrorInput } from "../../lib/utils"

const inputStyles = tv({
  base: [
    "relative block w-full appearance-none rounded-xl border px-3.5 py-2.5 shadow-sm outline-none transition sm:text-sm",
    "border-ink-700",
    "text-ink-200",
    "placeholder-ink-600",
    "bg-white",
    "disabled:border-ink-800 disabled:bg-ink-900 disabled:text-ink-600",
    "[&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden",
    focusInput,
  ],
  variants: {
    hasError: {
      true: hasErrorInput,
    },
    enableStepper: {
      false:
        "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
    },
  },
})

interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement>,
    VariantProps<typeof inputStyles> {
  inputClassName?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    { className, inputClassName, hasError, enableStepper = true, type, ...props },
    forwardedRef,
  ) => {
    const [typeState, setTypeState] = React.useState(type)
    const isPassword = type === "password"
    const isSearch = type === "search"

    return (
      <div className={cx("relative w-full", className)}>
        <input
          ref={forwardedRef}
          type={isPassword ? typeState : type}
          className={cx(
            inputStyles({ hasError, enableStepper }),
            { "pl-9": isSearch, "pr-10": isPassword },
            inputClassName,
          )}
          {...props}
        />
        {isSearch && (
          <div className="pointer-events-none absolute bottom-0 left-3 flex h-full items-center justify-center text-ink-600">
            <RiSearchLine className="size-4 shrink-0" aria-hidden="true" />
          </div>
        )}
        {isPassword && (
          <div className="absolute bottom-0 right-0 flex h-full items-center px-3">
            <button
              aria-label="Toggle password visibility"
              className={cx("h-fit w-fit rounded-sm text-ink-600 hover:text-ink-400 outline-none transition-all")}
              type="button"
              onClick={() => setTypeState(typeState === "password" ? "text" : "password")}
            >
              <span className="sr-only">
                {typeState === "password" ? "Show password" : "Hide password"}
              </span>
              {typeState === "password" ? (
                <RiEyeFill aria-hidden="true" className="size-4 shrink-0" />
              ) : (
                <RiEyeOffFill aria-hidden="true" className="size-4 shrink-0" />
              )}
            </button>
          </div>
        )}
      </div>
    )
  },
)

Input.displayName = "Input"

export { Input, inputStyles, type InputProps }
