import { useState } from "react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";

export function AlertSignup() {
  const [email, setEmail] = useState("");
  const [fuel, setFuel] = useState<FuelId>("petrol_92");
  const [threshold, setThreshold] = useState("380");
  const [direction, setDirection] = useState<"above" | "below">("below");
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
    setBusy(true);
    try {
      await api.subscribe({ email, fuel_type: fuel, threshold: t, direction });
      setStatus("ok");
      setMsg("You're subscribed. We'll email you when the threshold is met.");
      setEmail("");
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
              Set a threshold for any fuel type. We'll email you the moment a
              revision crosses your line.
            </p>
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
