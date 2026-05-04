import { useState } from "react";
import { RiCheckLine, RiFacebookBoxLine, RiFileCopyLine, RiWhatsappLine } from "@remixicon/react";
import { cx } from "../../lib/utils";

interface Props {
  text: string;
  url?: string;
  className?: string;
}

export function ShareButtons({ text, url = "https://octane.lk", className }: Props) {
  const [copied, setCopied] = useState(false);
  const full = `${text}\n\n${url}`;
  const waUrl = `https://wa.me/?text=${encodeURIComponent(full)}`;
  const fbUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${encodeURIComponent(text)}`;

  function copy() {
    navigator.clipboard.writeText(full).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className={cx("flex flex-wrap items-center gap-1.5", className)}>
      <span className="mr-0.5 text-xs text-ink-400">Share:</span>
      <a
        href={waUrl}
        target="_blank"
        rel="noopener noreferrer"
        title="Share on WhatsApp"
        className="flex items-center gap-1 rounded-lg border border-ink-800 px-2.5 py-1.5 text-xs text-ink-300 transition-colors hover:border-green-400 hover:text-green-600"
      >
        <RiWhatsappLine className="size-3.5" />
        <span>WhatsApp</span>
      </a>
      <a
        href={fbUrl}
        target="_blank"
        rel="noopener noreferrer"
        title="Share on Facebook"
        className="flex items-center gap-1 rounded-lg border border-ink-800 px-2.5 py-1.5 text-xs text-ink-300 transition-colors hover:border-blue-400 hover:text-blue-600"
      >
        <RiFacebookBoxLine className="size-3.5" />
        <span>Facebook</span>
      </a>
      <button
        onClick={copy}
        title="Copy to clipboard"
        className="flex items-center gap-1 rounded-lg border border-ink-800 px-2.5 py-1.5 text-xs text-ink-300 transition-colors hover:border-ink-600 hover:text-ink-200"
      >
        {copied ? (
          <>
            <RiCheckLine className="size-3.5 text-emerald-500" />
            <span className="text-emerald-500">Copied!</span>
          </>
        ) : (
          <>
            <RiFileCopyLine className="size-3.5" />
            <span>Copy</span>
          </>
        )}
      </button>
    </div>
  );
}
