"use client";

import { use, useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { BillingStatus, SubscriptionPlan } from "@/lib/types";
import { Alert, Button, Card, PageHeader } from "@/components/ui";

function fmtLimit(n: number) {
  return n === -1 ? "Unlimited" : n.toLocaleString();
}

export default function BillingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    const [p, s] = await Promise.all([
      api.listPlans(),
      api.billingStatus(id).catch(() => null),
    ]);
    setPlans(p.filter((x) => x.tier !== "enterprise").concat(p.filter((x) => x.tier === "enterprise")));
    setStatus(s);
  }, [id]);

  useEffect(() => {
    load().catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
    const q = new URLSearchParams(window.location.search).get("checkout");
    if (q === "success") setNotice("✓ Payment complete — your plan/credits update within a few seconds.");
    else if (q === "cancel") setNotice("Checkout canceled — no charge was made.");
    if (q) window.history.replaceState({}, "", window.location.pathname);
  }, [load]);

  async function go(url: string | null, after: () => void) {
    if (url) window.location.href = url;
    else {
      await load();
      after();
    }
  }

  async function choosePlan(tier: string) {
    setError("");
    setBusy(tier);
    try {
      const { url } = await api.billingCheckout(id, tier);
      await go(url, () => {});
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start checkout");
    } finally {
      setBusy("");
    }
  }

  async function buyCredits() {
    setError("");
    setBusy("credits");
    try {
      const { url } = await api.billingCreditsCheckout(id);
      await go(url, () => setNotice("Added render credits."));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not buy credits");
    } finally {
      setBusy("");
    }
  }

  async function openPortal() {
    setBusy("portal");
    try {
      const { url } = await api.billingPortal(id);
      if (url) window.location.href = url;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not open billing portal");
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader
        title="Billing & plan"
        subtitle="Manage your subscription, buy video-render credits, and see plan limits."
      />

      {notice && (
        <p className="mt-4 rounded-lg border border-brand/30 bg-brand/10 px-3 py-2 text-sm text-brand">
          {notice}
        </p>
      )}
      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      {status && !status.enabled && (
        <Card className="mt-4 border-amber-500/30 bg-amber-500/5">
          <p className="text-sm">
            <span className="font-medium">Billing isn&apos;t live yet (dev mode).</span>{" "}
            Plan checkout is disabled and &quot;Buy credits&quot; grants directly for
            testing. Add your Stripe keys to `.env` to enable real payments.
          </p>
        </Card>
      )}

      {/* Current plan + credits */}
      {status && (
        <Card className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Current plan</p>
              <p className="mt-1 text-lg font-semibold">
                {status.plan_name ?? "—"}
                {status.subscription_status && (
                  <span className="ml-2 text-xs font-normal text-muted">
                    ({status.subscription_status})
                  </span>
                )}
              </p>
              <p className="mt-1 text-sm text-muted">
                🎬 {status.video_credits} extra render credit
                {status.video_credits === 1 ? "" : "s"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={buyCredits} loading={busy === "credits"}>
                Buy 10 render credits
              </Button>
              {status.enabled && status.subscription_status && (
                <Button variant="ghost" onClick={openPortal} loading={busy === "portal"}>
                  Manage billing
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Plan tiers */}
      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {plans.map((p) => {
          const current = status?.plan_tier === p.tier;
          const enterprise = p.tier === "enterprise";
          return (
            <Card
              key={p.tier}
              className={"flex flex-col " + (current ? "ring-2 ring-brand" : "")}
            >
              <p className="text-sm font-semibold">{p.name}</p>
              <p className="mt-1 text-2xl font-bold">
                {enterprise ? (
                  "Custom"
                ) : (
                  <>
                    ${(p.price_monthly / 100).toFixed(2)}
                    <span className="text-sm font-normal text-muted">/mo</span>
                  </>
                )}
              </p>
              <ul className="mt-3 space-y-1.5 text-sm text-muted">
                <li>{fmtLimit(p.max_locations)} businesses</li>
                <li>{fmtLimit(p.max_social_accounts)} connected accounts</li>
                <li>{fmtLimit(p.max_users)} team seats</li>
                <li>{fmtLimit(p.ai_monthly_quota)} AI posts / mo</li>
                <li>{fmtLimit(p.image_monthly_quota)} images / mo</li>
                <li className="font-medium text-fg">
                  {fmtLimit(p.video_monthly_quota)} videos / mo
                </li>
                {p.features.white_label && <li>White-label</li>}
                {p.features.priority_support && <li>Priority support</li>}
              </ul>
              <div className="mt-auto pt-4">
                {current ? (
                  <Button variant="secondary" className="w-full" disabled>
                    Current plan
                  </Button>
                ) : enterprise ? (
                  <a
                    href="mailto:sales@example.com?subject=Enterprise plan"
                    className="block w-full rounded-lg border border-border py-2 text-center text-sm font-medium text-fg hover:bg-bg"
                  >
                    Contact sales
                  </a>
                ) : (
                  <Button
                    className="w-full"
                    onClick={() => choosePlan(p.tier)}
                    loading={busy === p.tier}
                  >
                    Choose {p.name}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </>
  );
}
