"use client";

import { useState } from "react";
import Link from "next/link";
import {
  CHANNEL_COLORS,
  CHANNEL_LABELS,
  type PlatformAnalytics,
} from "@/lib/types";
import { Card } from "@/components/ui";
import { LineChart } from "@/components/charts";

type Metric = "reach" | "engagement" | "clicks" | "mentions";
const METRIC_LABELS: Record<Metric, string> = {
  reach: "Reach",
  engagement: "Engagement",
  clicks: "Clicks",
  mentions: "Mentions",
};

const n = (v: number | undefined) => (v ?? 0).toLocaleString("en-US");

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-bg p-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-[11px] text-muted">{hint}</p>}
    </div>
  );
}

// Platform engagement metrics (reach, impressions, engagement rate, CTR, and
// Google Business actions). Simulated until live Meta/GBP connectors are approved.
export function PlatformPerformance({
  businessId,
  data,
}: {
  businessId: string;
  data: PlatformAnalytics;
}) {
  const s = data.social;
  const l = data.local;
  const hasSocial = (s.impressions ?? 0) > 0;
  const hasLocal = (l.views ?? 0) > 0 || (l.actions ?? 0) > 0;

  const [metric, setMetric] = useState<Metric>("reach");
  const chartSeries = data.series.platforms.map((p) => ({
    label: CHANNEL_LABELS[p.platform] ?? p.platform,
    color: CHANNEL_COLORS[p.platform] ?? CHANNEL_COLORS.generic,
    values: p[metric],
  }));

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Platform performance</h2>
        {data.simulated && (
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
            Sample data
          </span>
        )}
      </div>

      {!data.has_accounts ? (
        <p className="mt-3 text-sm text-muted">
          Connect your social accounts on the{" "}
          <Link href={`/businesses/${businessId}/schedule`} className="text-brand hover:underline">
            Schedule tab
          </Link>{" "}
          to see reach, engagement, clicks, and more.
        </p>
      ) : (
        <div className="mt-4 space-y-5">
          {hasSocial && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <Tile label="Reach" value={n(s.reach)} />
              <Tile label="Impressions" value={n(s.impressions)} />
              <Tile label="Engagement" value={`${s.engagement_rate ?? 0}%`} hint={`${n(s.engagements)} interactions`} />
              <Tile label="Clicks" value={n(s.link_clicks)} hint={`${s.ctr ?? 0}% CTR`} />
              <Tile label="Profile visits" value={n(s.profile_visits)} />
              <Tile
                label="Followers"
                value={n(s.followers)}
                hint={`${(s.follower_growth ?? 0) >= 0 ? "+" : ""}${n(s.follower_growth)} / 28d`}
              />
            </div>
          )}

          {hasLocal && (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
                Google Business
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Tile label="Views" value={n(l.views)} hint="Search + Maps" />
                <Tile label="Website clicks" value={n(l.website_clicks)} />
                <Tile label="Directions" value={n(l.direction_requests)} />
                <Tile label="Calls" value={n(l.calls)} />
              </div>
            </div>
          )}

          {/* Trend graph — one brand-colored line per platform; pick the metric. */}
          {chartSeries.length > 0 && (
            <div>
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted">
                  {METRIC_LABELS[metric]} by platform · last 8 weeks
                </p>
                <select
                  value={metric}
                  onChange={(e) => setMetric(e.target.value as Metric)}
                  className="rounded-lg border border-border bg-bg px-2.5 py-1.5 text-sm text-fg outline-none focus:border-brand"
                >
                  {(Object.keys(METRIC_LABELS) as Metric[]).map((m) => (
                    <option key={m} value={m}>
                      {METRIC_LABELS[m]}
                    </option>
                  ))}
                </select>
              </div>
              <LineChart labels={data.series.weeks} series={chartSeries} />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
