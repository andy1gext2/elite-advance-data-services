"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AdminUsage } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { Alert, Card } from "@/components/ui";

const usd = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const num = (n: number) => n.toLocaleString("en-US");

export default function AdminPage() {
  const router = useRouter();
  const { me, loading } = useAuth();
  const [data, setData] = useState<AdminUsage | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);

  async function setPlan(businessId: string, tier: string) {
    setError("");
    setSaving(businessId);
    try {
      await api.adminSetPlan(businessId, tier);
      const fresh = await api.adminUsage();
      setData(fresh);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not change plan");
    } finally {
      setSaving(null);
    }
  }

  // Client-side gate (the API enforces it server-side too). Non-admins are
  // bounced to their dashboard rather than shown a broken page.
  useEffect(() => {
    if (loading) return;
    if (!me) {
      router.replace("/login");
    } else if (!me.is_platform_admin) {
      router.replace("/dashboard");
    }
  }, [me, loading, router]);

  useEffect(() => {
    if (me?.is_platform_admin) {
      api
        .adminUsage()
        .then(setData)
        .catch((e) =>
          setError(e instanceof ApiError ? e.message : "Failed to load")
        );
    }
  }, [me]);

  if (loading || !me?.is_platform_admin) {
    return (
      <AppShell>
        <p className="text-muted">Loading…</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div>
        <h1 className="text-2xl font-semibold">Platform costs</h1>
        <p className="mt-1 text-sm text-muted">
          AI cost vs subscription revenue, per business, this month. Text cost is
          exact (from token usage); image/video are per-asset estimates.
        </p>
      </div>

      <Alert>{error}</Alert>

      {data && (
        <>
          {/* Totals */}
          <div className="mt-6 grid gap-4 sm:grid-cols-4">
            <Stat label="Businesses" value={num(data.totals.businesses)} />
            <Stat label="MRR" value={usd(data.totals.mrr_usd)} />
            <Stat label="AI cost (mo)" value={usd(data.totals.total_cost_usd)} />
            <Stat
              label="Gross margin"
              value={usd(data.totals.margin_usd)}
              tone={data.totals.margin_usd >= 0 ? "good" : "bad"}
            />
          </div>

          {/* Per-tenant table */}
          <Card className="mt-6 overflow-x-auto p-0">
            <table className="w-full min-w-[820px] text-sm">
              <thead className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Business</th>
                  <th className="px-4 py-3 font-medium">Plan</th>
                  <th className="px-4 py-3 text-right font-medium">Posts</th>
                  <th className="px-4 py-3 text-right font-medium">Tokens (in/out)</th>
                  <th className="px-4 py-3 text-right font-medium">Images</th>
                  <th className="px-4 py-3 text-right font-medium">Videos</th>
                  <th className="px-4 py-3 text-right font-medium">Cost</th>
                  <th className="px-4 py-3 text-right font-medium">MRR</th>
                  <th className="px-4 py-3 text-right font-medium">Margin</th>
                </tr>
              </thead>
              <tbody>
                {data.businesses.map((b) => (
                  <tr key={b.business_id} className="border-b border-border/60">
                    <td className="px-4 py-3 font-medium">{b.name}</td>
                    <td className="px-4 py-3">
                      <select
                        value={b.tier ?? ""}
                        onChange={(e) => setPlan(b.business_id, e.target.value)}
                        disabled={saving === b.business_id}
                        className="rounded-md border border-border bg-bg px-2 py-1 text-sm text-fg outline-none focus:border-brand"
                      >
                        <option value="starter">Starter</option>
                        <option value="professional">Professional</option>
                        <option value="growth">Growth</option>
                        <option value="enterprise">Enterprise ∞</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-right">{num(b.text_generations)}</td>
                    <td className="px-4 py-3 text-right text-muted">
                      {num(b.input_tokens)} / {num(b.output_tokens)}
                    </td>
                    <td className="px-4 py-3 text-right">{num(b.images)}</td>
                    <td className="px-4 py-3 text-right">{num(b.videos)}</td>
                    <td className="px-4 py-3 text-right">{usd(b.total_cost_usd)}</td>
                    <td className="px-4 py-3 text-right">{usd(b.mrr_usd)}</td>
                    <td
                      className={
                        "px-4 py-3 text-right font-medium " +
                        (b.margin_usd >= 0 ? "text-emerald-500" : "text-red-500")
                      }
                    >
                      {usd(b.margin_usd)}
                    </td>
                  </tr>
                ))}
                {data.businesses.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-muted">
                      No businesses yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </AppShell>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad";
}) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p
        className={
          "mt-1 text-2xl font-bold " +
          (tone === "good" ? "text-emerald-500" : tone === "bad" ? "text-red-500" : "")
        }
      >
        {value}
      </p>
    </Card>
  );
}
