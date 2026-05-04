import { useEffect, useState } from "react";
import { RiBellLine, RiCheckLine, RiExternalLinkLine } from "@remixicon/react";
import { api, FUEL_DISPLAY, FuelId, ManageAlertResp } from "../lib/api";
import { shortDate } from "../lib/format";
import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Button } from "../components/ui/Button";

export function ManageAlerts() {
  const token = new URLSearchParams(window.location.search).get("token") ?? "";

  const [alert, setAlert] = useState<ManageAlertResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unsubscribed, setUnsubscribed] = useState(false);
  const [unsubBusy, setUnsubBusy] = useState(false);

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
                {FUEL_DISPLAY[alert.fuel_type as FuelId]} alert
              </h1>

              <dl className="mt-6 grid grid-cols-2 gap-4">
                <div>
                  <dt className="label">Email</dt>
                  <dd className="mt-1 text-sm text-ink-200">{alert.email}</dd>
                </div>
                <div>
                  <dt className="label">Fuel</dt>
                  <dd className="mt-1 text-sm text-ink-200">
                    {FUEL_DISPLAY[alert.fuel_type as FuelId]}
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
                    {alert.active ? (
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

              <div className="mt-8 border-t border-ink-800 pt-6">
                {unsubscribed ? (
                  <div className="flex items-center gap-2 text-sm text-emerald-600">
                    <RiCheckLine className="size-4" />
                    Unsubscribed. You won't receive further emails for this alert.
                  </div>
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
                    <a
                      href="/#alerts"
                      className="flex items-center gap-1 text-sm text-ink-400 hover:text-ink-200 transition-colors"
                    >
                      Set a new alert
                      <RiExternalLinkLine className="size-3.5" />
                    </a>
                  </div>
                ) : (
                  <p className="text-sm text-ink-400">
                    This alert has already been cancelled.{" "}
                    <a href="/#alerts" className="text-accent hover:underline">
                      Set a new one?
                    </a>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
