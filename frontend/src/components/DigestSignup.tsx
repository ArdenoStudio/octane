import { useState } from "react";
import { RiMailLine } from "@remixicon/react";
import { api } from "../lib/api";

export function DigestSignup() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<null | "ok" | "err">(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setStatus("err");
      return;
    }
    setBusy(true);
    try {
      await api.subscribeDigest(email);
      setStatus("ok");
      setEmail("");
    } catch {
      setStatus("err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="container-x pt-12">
      <div className="rounded-2xl border border-ink-800 bg-ink-900/30 px-6 py-6 sm:px-8">
        <div className="flex flex-wrap items-center gap-6 sm:flex-nowrap">
          {/* Icon + text */}
          <div className="flex items-start gap-3 sm:flex-1">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-ink-800 bg-white">
              <RiMailLine className="size-4 text-accent" />
            </div>
            <div>
              <p className="font-semibold text-ink-100">Weekly digest</p>
              <p className="mt-0.5 text-sm text-ink-400">
                One email every Monday — current prices, weekly deltas, nothing else.
              </p>
            </div>
          </div>

          {/* Form */}
          {status === "ok" ? (
            <p className="text-sm text-emerald-600 font-medium">
              Subscribed — see you Monday.
            </p>
          ) : (
            <form onSubmit={submit} className="flex w-full items-center gap-2 sm:w-auto">
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input h-9 flex-1 min-w-0 sm:w-52 text-sm"
              />
              <button
                type="submit"
                disabled={busy}
                className="btn-primary h-9 shrink-0 text-sm disabled:opacity-60"
              >
                {busy ? "…" : "Subscribe"}
              </button>
            </form>
          )}

          {status === "err" && (
            <p className="w-full text-xs text-red-500 sm:hidden">
              Something went wrong — check your email and try again.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
