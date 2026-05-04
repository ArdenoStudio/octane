import * as React from "react"
import {
  RiArrowDownLine,
  RiArrowDownSFill,
  RiArrowRightLine,
  RiArrowRightSFill,
  RiArrowUpLine,
  RiArrowUpSFill,
} from "@remixicon/react"
import { cx } from "../../lib/utils"

type DeltaType = "increase" | "decrease" | "neutral"
type Variant = "outline" | "solid" | "solidOutline"
type IconStyle = "filled" | "line"

const variantDeltaClasses: Record<Variant, Record<DeltaType, string>> = {
  outline: {
    increase: "text-emerald-700 dark:text-emerald-500",
    decrease: "text-red-700 dark:text-red-500",
    neutral: "text-gray-700 dark:text-gray-400",
  },
  solid: {
    increase: "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/20 dark:text-emerald-500",
    decrease: "bg-red-100 text-red-800 dark:bg-red-400/20 dark:text-red-500",
    neutral: "bg-gray-200/50 text-gray-700 dark:bg-gray-500/30 dark:text-gray-300",
  },
  solidOutline: {
    increase: "bg-emerald-100 text-emerald-800 ring-emerald-600/10 dark:bg-emerald-400/20 dark:text-emerald-500 dark:ring-emerald-400/20",
    decrease: "bg-red-100 text-red-800 ring-red-600/10 dark:bg-red-400/20 dark:text-red-500 dark:ring-red-400/20",
    neutral: "bg-gray-100 text-gray-700 ring-gray-600/10 dark:bg-gray-500/30 dark:text-gray-300 dark:ring-gray-400/20",
  },
}

const variantBaseClasses: Record<Variant, string> = {
  outline: "gap-x-1 rounded px-2 py-1 ring-1 ring-inset ring-border",
  solid: "gap-x-1 rounded px-2 py-1",
  solidOutline: "gap-x-1 rounded px-2 py-1 ring-1 ring-inset",
}

const DeltaIcon = ({
  deltaType,
  iconStyle,
}: {
  deltaType: DeltaType
  iconStyle: IconStyle
}) => {
  const icons = {
    increase: { filled: RiArrowUpSFill, line: RiArrowUpLine },
    decrease: { filled: RiArrowDownSFill, line: RiArrowDownLine },
    neutral: { filled: RiArrowRightSFill, line: RiArrowRightLine },
  }
  const Icon = icons[deltaType][iconStyle]
  return <Icon className="-ml-0.5 size-4" aria-hidden={true} />
}

interface BadgeDeltaProps extends React.HTMLAttributes<HTMLSpanElement> {
  value: string | number
  variant?: Variant
  deltaType?: DeltaType
  iconStyle?: IconStyle
}

export function BadgeDelta({
  className,
  variant = "outline",
  deltaType = "neutral",
  iconStyle = "filled",
  value,
  ...props
}: BadgeDeltaProps) {
  return (
    <span
      className={cx(
        "inline-flex items-center text-xs font-semibold",
        variantBaseClasses[variant],
        variantDeltaClasses[variant][deltaType],
        className,
      )}
      {...props}
    >
      <DeltaIcon deltaType={deltaType} iconStyle={iconStyle} />
      {value}
    </span>
  )
}
