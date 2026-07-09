"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { CHANNEL_LABELS, type Business, type Dashboard, type Insights } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { BusinessTabs } from "@/components/BusinessTabs";
import { Alert, Button, Card } from "@/components/ui";
import { HBars, SentimentBar, WeeklyBars } from "@/components/charts";

function Delta({ now, prev }: { now: number; prev: number }) {
  const d = now - prev;
  if (d === 0) return <span className="text-muted">no change vs last month</span>;
  const up = d > 0;
  return (
    <span className={up ? "text-green-600 dark:text-green-500" : "text-red-500"}>
      {up ? "▲" : "▼"} {up ? "+" : ""}
      {d} vs last month
    </span>
  );
}

function Stat({
  label,
  value,
  sub,
  danger,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={"mt-1 text-2xl font-semibold " + (danger ? "text-red-500" : "")}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs">{sub}</p>}
    </Card>
  );
}

export default function BusinessDashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [business, setBusiness] = useState<Business | null>(null);
  const [data, setData] = useState<Dashboard | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [error, setError] = useState("");
  const [thinking, setThinking] = useState(false);

  const load = useCallback(async () => {
    const [biz, dash] = await Promise.all([
      api.getBusiness(id),
      api.dashboard(id),
    ]);
    setBusiness(biz);
    setData(dash);
  }, [id]);

  useEffect(() => {
    load().catch((e) =>
      setError(e instanceof ApiError ? e.message : "Failed to load")
    );
  }, [load]);

  async function askAi() {
    setError("");
    setThinking(true);
    try {
      setInsights(await api.generateInsights(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Insights failed");
    } finally {
      setThinking(false);
    }
  }

  const k = data?.kpis;
  const channelData = data
    ? Object.entries(data.content_by_channel)
        .map(([label, value]) => ({
          label: CHANNEL_LABELS[label] ?? label,
          value,
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <AppShell>
      <div className="mb-6 flex items-center gap-2 text-sm text-muted">
        <Link href="/dashboard" className="hover:text-fg">
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-fg">{business?.name ?? "…"}</span>
      </div>

      <BusinessTabs businessId={id} />

      <h1 className="mt-6 text-2xl font-semibold">Business dashboard</h1>
      <p className="mt-1 text-sm text-muted">
        Your marketing operations at a glance — content, publishing, and reputation.
      </p>

      <Alert>{error}</Alert>

      {!data || !k ? (
        <p className="mt-6 text-muted">Loading…</p>
      ) : (
        <>
          {/* KPI tiles */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Content created"
              value={k.total_content}
              sub={
                <Delta
                  now={data.trends.content_this_month}
                  prev={data.trends.content_last_month}
                />
              }
            />
            <Stat
              label="Published posts"
              value={k.published_posts}
              sub={<span className="text-muted">{k.pending_schedules} scheduled</span>}
            />
            <Stat
              label="Avg rating"
              value={
                <>
                  {k.average_rating.toFixed(1)}{" "}
                  <span className="text-base text-amber-500">★</span>
                </>
              }
              sub={
                <Delta
                  now={data.trends.reviews_this_month}
                  prev={data.trends.reviews_last_month}
                />
              }
            />
            <Stat
              label="Needs attention"
              value={k.needs_attention}
              danger={k.needs_attention > 0}
              sub={
                <span className="text-muted">
                  {Math.round(k.response_rate * 100)}% response rate
                </span>
              }
            />
          </div>

          {/* Charts */}
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="text-sm font-semibold">Content created / week</h3>
              <p className="mb-3 text-xs text-muted">Last 8 weeks</p>
              <WeeklyBars data={data.timeseries.content_per_week} />
            </Card>
            <Card>
              <h3 className="text-sm font-semibold">Reviews / week</h3>
              <p className="mb-3 text-xs text-muted">Last 8 weeks</p>
              <WeeklyBars data={data.timeseries.reviews_per_week} />
            </Card>
            <Card>
              <h3 className="mb-3 text-sm font-semibold">Content by channel</h3>
              <HBars data={channelData} />
            </Card>
            <Card>
              <h3 className="mb-3 text-sm font-semibold">Review sentiment</h3>
              <SentimentBar s={data.sentiment} />
            </Card>
          </div>

          {/* Recommendations + AI insights */}
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="text-sm font-semibold">Recommended actions</h3>
              {data.recommendations.length === 0 ? (
                <p className="mt-3 text-sm text-muted">
                  You&apos;re all caught up — nothing needs attention right now.
                </p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {data.recommendations.map((r, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <span className="text-brand">→</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">AI business consultant</h3>
                <Button variant="secondary" onClick={askAi} loading={thinking}>
                  ✨ How am I doing?
                </Button>
              </div>
              {insights ? (
                <p className="mt-3 whitespace-pre-wrap text-sm text-fg/90">
                  {insights.summary}
                </p>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  Ask the AI to review your metrics and give a candid assessment
                  with next steps.
                </p>
              )}
            </Card>
          </div>
        </>
      )}
    </AppShell>
  );
}
