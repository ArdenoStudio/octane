import * as AccordionPrimitives from "@radix-ui/react-accordion"
import { RiAddLine } from "@remixicon/react"
import React from "react"
import { cx } from "../../lib/utils"

const Accordion = AccordionPrimitives.Root

const AccordionTrigger = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitives.Trigger>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitives.Trigger>
>(({ className, children, ...props }, forwardedRef) => (
  <AccordionPrimitives.Header className="flex">
    <AccordionPrimitives.Trigger
      className={cx(
        "group flex flex-1 cursor-pointer items-center justify-between py-3 text-left text-sm font-medium leading-none",
        "text-ink-200",
        "data-[disabled]:cursor-default data-[disabled]:text-ink-600",
        "focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-amber-400",
        className,
      )}
      {...props}
      ref={forwardedRef}
    >
      {children}
      <RiAddLine
        className={cx(
          "size-5 shrink-0 transition-transform duration-150 ease-[cubic-bezier(0.87,_0,_0.13,_1)] group-data-[state=open]:-rotate-45",
          "text-ink-600",
          "group-data-[disabled]:text-ink-800",
        )}
        aria-hidden="true"
        focusable="false"
      />
    </AccordionPrimitives.Trigger>
  </AccordionPrimitives.Header>
))

AccordionTrigger.displayName = "AccordionTrigger"

const AccordionContent = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitives.Content>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitives.Content>
>(({ className, children, ...props }, forwardedRef) => (
  <AccordionPrimitives.Content
    ref={forwardedRef}
    className="transform-gpu data-[state=closed]:animate-accordionClose data-[state=open]:animate-accordionOpen"
    {...props}
  >
    <div className={cx("overflow-hidden pb-4 text-sm text-ink-400", className)}>
      {children}
    </div>
  </AccordionPrimitives.Content>
))

AccordionContent.displayName = "AccordionContent"

const AccordionItem = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitives.Item>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitives.Item>
>(({ className, ...props }, forwardedRef) => (
  <AccordionPrimitives.Item
    ref={forwardedRef}
    className={cx("overflow-hidden border-b border-ink-800 first:mt-0", className)}
    {...props}
  />
))

AccordionItem.displayName = "AccordionItem"

export { Accordion, AccordionContent, AccordionItem, AccordionTrigger }
