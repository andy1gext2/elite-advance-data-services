"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  CHANNEL_COLORS,
  CHANNEL_LABELS,
  type CampaignCalendarItem,
  type ContentItem,
  type Dashboard,
  type Insights,
  type PlatformAnalytics,
  type Review,
} from "@/lib/types";
import { Alert, Button, Card, PageHeader } from "@/components/ui";
import { Donut, SentimentBar, WeeklyBars } from "@/components/charts";
import { PlatformPerformance } from "@/components/PlatformPerformance";
import { PlatformDetailModal } from "@/components/PlatformDetailModal";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

// "2026-07-14T11:00:00" → "Jul 14 · 11:00" (parsed from parts, no tz shift).
function fmtWhen(iso: string, withTime = true) {
  const [date, time] = iso.split("T");
  const [, mo, da] = date.split("-").map(Number);
  const hm = (time ?? "").slice(0, 5);
  return `${MONTHS[mo - 1]} ${da}${withTime && hm ? ` · ${hm}` : ""}`;
}

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

function Kpi({
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
    <div className="relative overflow-hidden rounded-xl border border-border bg-surface p-4 shadow-sm">
      <span
        className={
          "absolute inset-x-0 top-0 h-1 " + (danger ? "bg-red-500" : "bg-brand")
        }
      />
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
        {label}
      </p>
      <p className={"mt-1.5 text-2xl font-semibold tabular-nums " + (danger ? "text-red-500" : "")}>
        {value}
      </p>
      {sub && <p className="mt-1 text-xs">{sub}</p>}
    </div>
  );
}

function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2">
      <h3 className="text-sm font-semibold">{children}</h3>
      {action}
    </div>
  );
}

type Activity = { key: string; icon: string; text: string; when?: string };

export default function BusinessDashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<Dashboard | null>(null);
  const [calendar, setCalendar] = useState<CampaignCalendarItem[]>([]);
  const [content, setContent] = useState<ContentItem[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [platform, setPlatform] = useState<PlatformAnalytics | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [error, setError] = useState("");
  const [thinking, setThinking] = useState(false);
  // Channel drilled into from the wheel → opens the per-platform detail view.
  const [drillChannel, setDrillChannel] = useState<string | null>(null);

  const load = useCallback(async () => {
    // Dashboard is required; the feed/strip sources are best-effort.
    const [dash, cal, items, revs, plat] = await Promise.all([
      api.dashboard(id),
      api.campaignCalendar(id).catch(() => [] as CampaignCalendarItem[]),
      api.listContent(id).catch(() => [] as ContentItem[]),
      api.listReviews(id).catch(() => [] as Review[]),
      api.platformAnalytics(id).catch(() => null),
    ]);
    setData(dash);
    setCalendar(cal);
    setContent(items);
    setReviews(revs);
    setPlatform(plat);
  }, [id]);

  useEffect(() => {
    load().catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
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
        .map(([channel, value]) => ({
          key: channel,
          label: CHANNEL_LABELS[channel] ?? channel,
          value,
          color: CHANNEL_COLORS[channel] ?? CHANNEL_COLORS.generic,
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  const todayKey = (() => {
    const n = new Date();
    return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-${String(n.getDate()).padStart(2, "0")}`;
  })();

  const upcoming = calendar
    .filter((c) => c.scheduled_at.slice(0, 10) >= todayKey)
    .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at))
    .slice(0, 8);

  // A recent-activity feed woven from reviews, upcoming posts, and fresh drafts.
  const feed: Activity[] = [
    ...[...reviews]
      .sort((a, b) => (b.reviewed_at ?? "").localeCompare(a.reviewed_at ?? ""))
      .slice(0, 3)
      .map((r) => ({
        key: `r-${r.id}`,
        icon: r.rating >= 4 ? "⭐" : "⚠️",
        text: `${r.rating}★ review from ${r.author_name ?? "a customer"}`,
        when: r.reviewed_at ? fmtWhen(r.reviewed_at, false) : undefined,
      })),
    ...upcoming.slice(0, 3).map((c) => ({
      key: `u-${c.id}`,
      icon: "📅",
      text: `${CHANNEL_LABELS[c.channel] ?? c.channel} post scheduled`,
      when: fmtWhen(c.scheduled_at),
    })),
    ...content.slice(0, 3).map((it) => ({
      key: `c-${it.id}`,
      icon: "✍️",
      text: `New ${CHANNEL_LABELS[it.channel] ?? it.channel} draft`,
    })),
  ].slice(0, 7);

  return (
    <>
      <PageHeader
        title="Business dashboard"
        subtitle="Your marketing command center — content, publishing, and reputation at a glance."
        action={
          <Button variant="secondary" onClick={askAi} loading={thinking}>
            ✨ How am I doing?
          </Button>
        }
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      {insights && (
        <Card className="mt-4 border-brand/30 bg-brand/5">
          <SectionTitle>AI business consultant</SectionTitle>
          <p className="whitespace-pre-wrap text-sm text-fg/90">{insights.summary}</p>
        </Card>
      )}

      {!data || !k ? (
        <p className="mt-6 text-muted">Loading…</p>
      ) : (
        <>
          {/* KPI row */}
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi
              label="Content created"
              value={k.total_content}
              sub={<Delta now={data.trends.content_this_month} prev={data.trends.content_last_month} />}
            />
            <Kpi
              label="Published posts"
              value={k.published_posts}
              sub={<span className="text-muted">{k.pending_schedules} scheduled</span>}
            />
            <Kpi
              label="Avg rating"
              value={
                <>
                  {k.average_rating.toFixed(1)} <span className="text-base text-amber-500">★</span>
                </>
              }
              sub={<Delta now={data.trends.reviews_this_month} prev={data.trends.reviews_last_month} />}
            />
            <Kpi
              label="Needs attention"
              value={k.needs_attention}
              danger={k.needs_attention > 0}
              sub={<span className="text-muted">{Math.round(k.response_rate * 100)}% response rate</span>}
            />
          </div>

          {/* Top row: platform performance (3/4) + the channel wheel (1/4). */}
          <div className="mt-4 grid gap-4 lg:grid-cols-4">
            {platform && (
              <div className="lg:col-span-3">
                <PlatformPerformance businessId={id} data={platform} />
              </div>
            )}
            <Card className={platform ? "lg:col-span-1" : "lg:col-span-1 lg:col-start-4"}>
              <SectionTitle>Content by channel</SectionTitle>
              <div className="flex justify-center py-1">
                <Donut data={channelData} size={116} onSelect={setDrillChannel} />
              </div>
              <p className="mt-2 text-center text-[11px] text-muted">
                Click a channel for its analytics
              </p>
            </Card>
          </div>

          {/* Content performance + activity rail + sentiment. */}
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <SectionTitle action={<span className="text-xs text-muted">Last 8 weeks</span>}>
                Content performance
              </SectionTitle>
              <WeeklyBars data={data.timeseries.content_per_week} />
            </Card>

            <Card className="lg:row-span-2">
              <SectionTitle>Activity feed</SectionTitle>
              {feed.length === 0 ? (
                <p className="text-sm text-muted">
                  Nothing yet — draft a campaign and it&apos;ll show up here.
                </p>
              ) : (
                <ul className="space-y-3">
                  {feed.map((a) => (
                    <li key={a.key} className="flex gap-2.5 text-sm">
                      <span className="shrink-0 leading-5">{a.icon}</span>
                      <div className="min-w-0">
                        <p className="truncate text-fg/90">{a.text}</p>
                        {a.when && <p className="text-xs text-muted">{a.when}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="lg:col-span-2">
              <SectionTitle>Review sentiment</SectionTitle>
              <SentimentBar s={data.sentiment} />
            </Card>
          </div>

          {/* Upcoming posts strip */}
          <Card className="mt-4">
            <SectionTitle
              action={
                <Link href={`/businesses/${id}/calendar`} className="text-xs text-brand hover:underline">
                  Open calendar →
                </Link>
              }
            >
              Upcoming posts
            </SectionTitle>
            {upcoming.length === 0 ? (
              <p className="text-sm text-muted">
                No scheduled posts.{" "}
                <Link href={`/businesses/${id}/content`} className="text-brand hover:underline">
                  Draft a campaign
                </Link>{" "}
                to fill your calendar.
              </p>
            ) : (
              <div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-1">
                {upcoming.map((c) => (
                  <div
                    key={c.id}
                    className="w-52 shrink-0 rounded-lg border border-border bg-bg p-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-brand">
                        {CHANNEL_LABELS[c.channel] ?? c.channel}
                      </span>
                      <span className="text-[11px] text-muted">{fmtWhen(c.scheduled_at)}</span>
                    </div>
                    <p className="mt-1.5 line-clamp-3 text-xs text-fg/80">
                      {c.title || c.body || "—"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Recommendations */}
          <Card className="mt-4">
            <SectionTitle>Recommended actions</SectionTitle>
            {data.recommendations.length === 0 ? (
              <p className="text-sm text-muted">
                You&apos;re all caught up — nothing needs attention right now.
              </p>
            ) : (
              <ul className="space-y-2">
                {data.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="text-brand">→</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Per-platform drill-down opened from the channel wheel. */}
          {drillChannel && (
            <PlatformDetailModal
              businessId={id}
              channel={drillChannel}
              postCount={data.content_by_channel[drillChannel] ?? 0}
              analytics={platform}
              onClose={() => setDrillChannel(null)}
            />
          )}
        </>
      )}
    </>
  );
}
