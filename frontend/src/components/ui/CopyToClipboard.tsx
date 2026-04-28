import { RiCheckLine, RiFileCopy2Line } from "@remixicon/react"
import React from "react"

export function CopyToClipboard({ code }: { code: string }) {
  const [copied, setCopied] = React.useState(false)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
    } catch (error) {
      console.error("Error copying to clipboard", error)
    } finally {
      setTimeout(() => setCopied(false), 1500)
    }
  }

  return (
    <button
      onClick={copyToClipboard}
      title="Copy to clipboard"
      className="select-none rounded-lg border border-ink-700 bg-ink-900 p-1.5 transition hover:bg-ink-800"
    >
      {!copied ? (
        <RiFileCopy2Line aria-hidden="true" className="size-4 text-ink-400" />
      ) : (
        <RiCheckLine aria-hidden="true" className="size-4 text-emerald-500" />
      )}
    </button>
  )
}
