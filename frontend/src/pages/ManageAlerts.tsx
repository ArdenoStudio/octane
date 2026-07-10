import { useEffect, useState } from "react";
import {
  RiBellLine,
  RiCheckLine,
  RiExternalLinkLine,
  RiPencilLine,
} from "@remixicon/react";
import { api, FuelId, ManageAlertResp, FUEL_ORDER } from "../lib/api";
import { useFuelLabel } from "../i18n/LocaleProvider";
import { shortDate } from "../lib/format";
import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

function FireHistory({ fires }: { fires: ManageAlertResp["fire_history"] }) {
  if (fires.length === 0) return null;
  return (
    <div className="mt-8 border-t border-ink-800 pt-6">
      <p className="label mb-3">Alert history</p>
      <ul className="space-y-2">
        {fires.map((f, i) => (
          <li key={i} className="flex items-center justify-between text-sm">
            <span className="text-ink-400">{shortDate(f.fired_at)}</span>
            <span className="font-semibold text-ink-200">LKR {f.price_lkr}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EditForm({
  alert,
  token,
  onSave,
  onCancel,
}: {
  alert: ManageAlertResp;
  token: string;
  onSave: (threshold: number, direction: "above" | "below") => void;
  onCancel: () => void;
}) {
  const [threshold, setThreshold] = useState(String(alert.threshold));
  const [direction, setDirection] = useState<"above" | "below">(alert.direction);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = parseFloat(threshold);
    if (!(t > 0)) {
      setErr("Enter a valid threshold.");
      return;
    }
    setBusy(true);
    try {
      await api.updateAlert(token, { threshold: t, direction });
      onSave(t, direction);
    } catch {
      setErr("Failed to update. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-8 border-t border-ink-800 pt-6 space-y-4">
      <p className="label">Edit alert</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">When price goes</label>
          <select
            className="input mt-2"
            value={direction}
            onChange={(e) => setDirection(e.target.value as "above" | "below")}
          >
            <option value="below">below</option>
            <option value="above">above</option>
          </select>
        </div>
        <div>
          <label className="label">Threshold (LKR)</label>
          <Input
            className="mt-2"
            inputMode="decimal"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button type="submit" isLoading={busy} loadingText="Saving…">
          Save changes
        </Button>
        <button
          type="button"
          onClick={onCancel}
          className="text-sm text-ink-400 hover:text-ink-200 transition-colors"
        >
          Cancel
        </button>
        {err && <span className="text-sm text-red-500">{err}</span>}
      </div>
    </form>
  );
}

function ResubscribeForm({ fuelType }: { fuelType: FuelId }) {
  const fuelLabel = useFuelLabel();
  const [email, setEmail] = useState("");
  const [fuel, setFuel] = useState<FuelId>(fuelType);
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
      setMsg("Check your email to confirm the new alert.");
    } catch (err) {
      setStatus("err");
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-8 border-t border-ink-800 pt-6">
      <p className="label mb-3">Set a new alert</p>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Email</label>
          <Input
            type="email"
            className="mt-2"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Fuel</label>
            <select
              className="input mt-2"
              value={fuel}
              onChange={(e) => setFuel(e.target.value as FuelId)}
            >
              {FUEL_ORDER.map((f) => (
                <option key={f} value={f}>{fuelLabel(f)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">When price goes</label>
            <select
              className="input mt-2"
              value={direction}
              onChange={(e) => setDirection(e.target.value as "above" | "below")}
            >
              <option value="below">below</option>
              <option value="above">above</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">Threshold (LKR)</label>
          <Input
            className="mt-2"
            inputMode="decimal"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" isLoading={busy} loadingText="Subscribing…">
            <RiBellLine className="mr-1.5 size-4" />
            Notify me
          </Button>
          {status === "ok" && <span className="text-sm text-emerald-600">{msg}</span>}
          {status === "err" && <span className="text-sm text-red-500">{msg}</span>}
        </div>
      </form>
    </div>
  );
}

export function ManageAlerts() {
  const fuelLabel = useFuelLabel();
  const token = new URLSearchParams(window.location.search).get("token") ?? "";

  useEffect(() => {
    document.title = "Manage Alerts — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

  const [alert, setAlert] = useState<ManageAlertResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unsubscribed, setUnsubscribed] = useState(false);
  const [unsubBusy, setUnsubBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("No token provided. Use the link from your alert email.");
      setLoading(false);
      return;
    }
    api
      .manageAlert(token)
      .then((r) => {
        setAlert(r);
        setLoading(false);
      })
      .catch(() => {
        setError("Alert not found. It may have already been cancelled, or the link is invalid.");
        setLoading(false);
      });
  }, [token]);

  async function handleUnsubscribe() {
    setUnsubBusy(true);
    try {
      await api.unsubscribeAlert(token);
      setUnsubscribed(true);
      if (alert) setAlert({ ...alert, active: false });
    } catch {
      setError("Failed to unsubscribe. Please try again.");
    } finally {
      setUnsubBusy(false);
    }
  }

  function handleSaveEdit(threshold: number, direction: "above" | "below") {
    if (alert) setAlert({ ...alert, threshold, direction });
    setEditing(false);
    setSaveOk(true);
    setTimeout(() => setSaveOk(false), 3000);
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="container-x py-16">
        <div className="mx-auto max-w-lg">
          <a
            href="/"
            className="mb-8 inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-200 transition-colors"
          >
            ← Back to Octane
          </a>

          {loading && (
            <div className="card p-8 text-center text-ink-400">
              Loading alert…
            </div>
          )}

          {error && !loading && (
            <div className="card p-8 text-center">
              <p className="text-ink-300">{error}</p>
              <a
                href="/"
                className="mt-4 inline-block text-sm text-accent hover:underline"
              >
                Go back to Octane
              </a>
            </div>
          )}

          {alert && !loading && (
            <div className="card p-6 sm:p-8">
              <div className="label">Manage alert</div>
              <h1 className="mt-2 font-display text-2xl font-extrabold tracking-tightest text-ink-100 sm:text-3xl">
                {fuelLabel(alert.fuel_type as FuelId)} alert
              </h1>

              {!alert.confirmed && (
                <div className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700">
                  Check your inbox — you need to confirm this alert before it activates.
                </div>
              )}

              <dl className="mt-6 grid grid-cols-2 gap-4">
                <div>
                  <dt className="label">Email</dt>
                  <dd className="mt-1 text-sm text-ink-200">{alert.email}</dd>
                </div>
                <div>
                  <dt className="label">Fuel</dt>
                  <dd className="mt-1 text-sm text-ink-200">
                    {fuelLabel(alert.fuel_type as FuelId)}
                  </dd>
                </div>
                <div>
                  <dt className="label">Trigger</dt>
                  <dd className="mt-1 text-sm text-ink-200">
                    Price goes {alert.direction} LKR {alert.threshold.toFixed(2)}
                  </dd>
                </div>
                <div>
                  <dt className="label">Status</dt>
                  <dd className="mt-1 text-sm">
                    {!alert.confirmed ? (
                      <span className="text-amber-600 font-semibold">Pending confirmation</span>
                    ) : alert.active ? (
                      <span className="text-emerald-600 font-semibold">Active</span>
                    ) : (
                      <span className="text-ink-400">Cancelled</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="label">Created</dt>
                  <dd className="mt-1 text-sm text-ink-200">
                    {shortDate(alert.created_at)}
                  </dd>
                </div>
              </dl>

              {/* Fire history */}
              <FireHistory fires={alert.fire_history} />

              {/* Edit form */}
              {editing && alert.active && (
                <EditForm
                  alert={alert}
                  token={token}
                  onSave={handleSaveEdit}
                  onCancel={() => setEditing(false)}
                />
              )}

              {/* Actions */}
              {!editing && (
                <div className="mt-8 border-t border-ink-800 pt-6">
                  {unsubscribed ? (
                    <>
                      <div className="flex items-center gap-2 text-sm text-emerald-600">
                        <RiCheckLine className="size-4" />
                        Unsubscribed. You won't receive further emails for this alert.
                      </div>
                      <ResubscribeForm fuelType={alert.fuel_type} />
                    </>
                  ) : alert.active ? (
                    <div className="flex flex-wrap items-center gap-4">
                      <Button
                        variant="destructive"
                        onClick={handleUnsubscribe}
                        isLoading={unsubBusy}
                        loadingText="Cancelling…"
                      >
                        <RiBellLine className="mr-1.5 size-4" />
                        Unsubscribe
                      </Button>
                      <button
                        onClick={() => setEditing(true)}
                        className="flex items-center gap-1.5 text-sm text-ink-400 hover:text-ink-200 transition-colors"
                      >
                        <RiPencilLine className="size-3.5" />
                        Edit threshold
                      </button>
                      {saveOk && (
                        <span className="flex items-center gap-1 text-sm text-emerald-600">
                          <RiCheckLine className="size-4" /> Saved
                        </span>
                      )}
                      <a
                        href="/#alerts"
                        className="flex items-center gap-1 text-sm text-ink-400 hover:text-ink-200 transition-colors"
                      >
                        Set a new alert
                        <RiExternalLinkLine className="size-3.5" />
                      </a>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm text-ink-400">
                        This alert has already been cancelled.
                      </p>
                      <ResubscribeForm fuelType={alert.fuel_type} />
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
