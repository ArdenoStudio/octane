import React, { useEffect, useRef, useState } from "react"

function useFadeIn(delay = 0) {
  const ref = useRef<HTMLDivElement & HTMLSpanElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          const timer = setTimeout(() => setVisible(true), delay)
          observer.disconnect()
          return () => clearTimeout(timer)
        }
      },
      { threshold: 0.1 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [delay])

  return { ref, visible }
}

const fadeStyle = (visible: boolean): React.CSSProperties => ({
  opacity: visible ? 1 : 0,
  transform: visible ? "translateY(0)" : "translateY(12px)",
  filter: visible ? "blur(0px)" : "blur(3px)",
  transition: "opacity 0.4s ease, transform 0.4s ease, filter 0.4s ease",
})

export function FadeContainer({
  children,
  className,
}: React.HTMLProps<HTMLDivElement>) {
  return <div className={className}>{children}</div>
}

export function FadeDiv({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  const { ref, visible } = useFadeIn(delay)
  return (
    <div ref={ref} className={className} style={fadeStyle(visible)}>
      {children}
    </div>
  )
}

export function FadeSpan({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  const { ref, visible } = useFadeIn(delay)
  return (
    <span ref={ref} className={className} style={fadeStyle(visible)}>
      {children}
    </span>
  )
}
