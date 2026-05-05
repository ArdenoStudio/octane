import { useState } from "react";
import { RiTelegramLine } from "@remixicon/react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";

export function AlertSignup() {
  const [email, setEmail] = useState("");
  const [fuel, setFuel] = useState<FuelId>("petrol_92");
  const [threshold, setThreshold] = useState("380");
  const [direction, setDirection] = useState<"above" | "below">("below");
  const [tgEnabled, setTgEnabled] = useState(false);
  const [tgChatId, setTgChatId] = useState("");
  const [status, setStatus] = useState<null | "ok" | "err">(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = parseFloat(threshold);
    if (!email.includes("@") || !(t > 0)) {
      setStatus("err");
      setMsg("Check your email and threshold.");
      return;
    }
    if (tgEnabled && !tgChatId.trim()) {
      setStatus("err");
      setMsg("Enter your Telegram chat ID or disable that option.");
      return;
    }
    setBusy(true);
    try {
      await api.subscribe({
        email,
        fuel_type: fuel,
        threshold: t,
        direction,
        telegram_chat_id: tgEnabled && tgChatId.trim() ? tgChatId.trim() : undefined,
      });
      setStatus("ok");
      setMsg("You're in. You'll be notified the moment prices cross your threshold.");
      setEmail("");
      setTgChatId("");
      setTgEnabled(false);
    } catch (err) {
      setStatus("err");
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="alerts" className="container-x pt-16">
      <div className="card p-6 sm:p-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <div className="label">Get notified</div>
            <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
              Don't get caught by a price hike.
            </h2>
            <p className="mt-3 text-ink-300">
              Set a price target. We'll send you an email — and optionally a
              Telegram message — the moment CPC revises that fuel past your
              threshold. Free, no spam.
            </p>
            <p className="mt-2 text-xs text-ink-500">Free · Unsubscribe anytime</p>
          </div>

          <form onSubmit={submit} className="lg:col-span-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="email" className="label">Email</label>
                <Input
                  id="email"
                  type="email"
                  className="mt-2"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div>
                <label htmlFor="alert-fuel" className="label">Fuel</label>
                <select
                  id="alert-fuel"
                  className="input mt-2"
                  value={fuel}
                  onChange={(e) => setFuel(e.target.value as FuelId)}
                >
                  {FUEL_ORDER.map((f) => (
                    <option key={f} value={f}>{FUEL_DISPLAY[f]}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="direction" className="label">When price goes</label>
                <select
                  id="direction"
                  className="input mt-2"
                  value={direction}
                  onChange={(e) => setDirection(e.target.value as "above" | "below")}
                >
                  <option value="below">below</option>
                  <option value="above">above</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="threshold" className="label">Threshold (LKR)</label>
                <Input
                  id="threshold"
                  className="mt-2"
                  inputMode="decimal"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                />
              </div>
            </div>

            {/* ── Telegram opt-in ── */}
            <div className="mt-4 rounded-xl border border-ink-800 p-4">
              <button
                type="button"
                onClick={() => setTgEnabled((v) => !v)}
                className="flex w-full items-center justify-between gap-2 text-left"
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-ink-200">
                  <RiTelegramLine className="size-4 text-[#2aabee]" />
                  Also notify me on Telegram
                </span>
                <span
                  className={`inline-flex h-5 w-9 items-center rounded-full border transition-colors ${
                    tgEnabled
                      ? "border-accent bg-accent"
                      : "border-ink-700 bg-ink-900"
                  }`}
                >
                  <span
                    className={`h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
                      tgEnabled ? "translate-x-4" : "translate-x-0.5"
                    }`}
                  />
                </span>
              </button>

              {tgEnabled && (
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-ink-400 leading-relaxed">
                    1.{" "}
                    <a
                      href="https://t.me/OctaneLKBot"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#2aabee] hover:underline"
                    >
                      Open @OctaneLKBot
                    </a>{" "}
                    and send <code className="rounded bg-ink-900 px-1 py-0.5 text-ink-200">/start</code>.
                    <br />
                    2. The bot replies with your chat ID — paste it below.
                  </p>
                  <Input
                    type="text"
                    placeholder="Your Telegram chat ID (e.g. 123456789)"
                    value={tgChatId}
                    onChange={(e) => setTgChatId(e.target.value)}
                    inputMode="numeric"
                    className="mt-1"
                  />
                </div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button type="submit" isLoading={busy} loadingText="Subscribing…">
                Notify me
              </Button>
              {status === "ok" && (
                <span className="text-sm text-emerald-600">{msg}</span>
              )}
              {status === "err" && (
                <span className="text-sm text-red-500">{msg}</span>
              )}
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}
