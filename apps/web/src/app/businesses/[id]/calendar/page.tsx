"use client";

import { use, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  CHANNEL_LABELS,
  type CampaignCalendarItem,
  type ContentItem,
} from "@/lib/types";
import { PostEditModal } from "@/components/PostEditModal";
import { Alert, Card, PageHeader } from "@/components/ui";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// Status → a small dot color for the bird's-eye view.
const STATUS_DOT: Record<string, string> = {
  scheduled: "bg-green-500",
  published: "bg-green-500",
  proposed: "bg-amber-500",
  skipped: "bg-zinc-400",
};

function dayKey(y: number, m: number, d: number) {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export default function CalendarPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [entries, setEntries] = useState<CampaignCalendarItem[]>([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<CampaignCalendarItem | null>(null);
  const [dragOverKey, setDragOverKey] = useState<string | null>(null);

  // Drag a post onto a day → move it there (keeping its time). Optimistic, with
  // a revert if the server rejects it.
  async function reschedule(itemId: string, key: string) {
    const entry = entries.find((e) => e.id === itemId);
    if (!entry || entry.scheduled_at.slice(0, 10) === key) return;
    const prev = entries;
    setEntries((list) =>
      list.map((e) =>
        e.id === itemId ? { ...e, scheduled_at: key + e.scheduled_at.slice(10) } : e
      )
    );
    try {
      await api.rescheduleCalendarItem(id, itemId, key);
    } catch (err) {
      setEntries(prev);
      setError(err instanceof ApiError ? err.message : "Could not move that post");
    }
  }

  // Reflect an edited post back into the calendar.
  function onPostSaved(updated: ContentItem) {
    setEntries((list) =>
      list.map((e) =>
        e.content_item_id === updated.id
          ? { ...e, title: updated.title, body: updated.body }
          : e
      )
    );
  }

  const today = new Date();
  const [view, setView] = useState({
    year: today.getFullYear(),
    month: today.getMonth(),
  });

  useEffect(() => {
    api
      .campaignCalendar(id)
      .then(setEntries)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, [id]);

  // Group posts by their calendar day (parse the date part directly — no tz shift).
  const byDay = useMemo(() => {
    const map = new Map<string, CampaignCalendarItem[]>();
    for (const e of entries) {
      const key = e.scheduled_at.slice(0, 10);
      (map.get(key) ?? map.set(key, []).get(key)!).push(e);
    }
    return map;
  }, [entries]);

  // Build the trailing/leading cells for the month grid.
  const cells = useMemo(() => {
    const first = new Date(view.year, view.month, 1).getDay();
    const days = new Date(view.year, view.month + 1, 0).getDate();
    const out: (number | null)[] = [];
    for (let i = 0; i < first; i++) out.push(null);
    for (let d = 1; d <= days; d++) out.push(d);
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }, [view]);

  const monthCount = entries.filter((e) => {
    const [y, m] = e.scheduled_at.split("-").map(Number);
    return y === view.year && m - 1 === view.month;
  }).length;

  function shift(delta: number) {
    setView((v) => {
      const d = new Date(v.year, v.month + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() };
    });
  }

  const todayKey = dayKey(today.getFullYear(), today.getMonth(), today.getDate());

  return (
    <>
      <PageHeader
        title="Campaign calendar"
        subtitle={
          <>
            A bird&apos;s-eye view of every scheduled post across your campaigns.
            Build campaigns from the{" "}
            <Link href={`/businesses/${id}/content`} className="text-brand hover:underline">
              Content
            </Link>{" "}
            tab.
          </>
        }
        action={
          <div className="flex items-center gap-1">
            <button
              onClick={() => shift(-1)}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted hover:text-fg"
              aria-label="Previous month"
            >
              ‹
            </button>
            <button
              onClick={() => setView({ year: today.getFullYear(), month: today.getMonth() })}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted hover:text-fg"
            >
              Today
            </button>
            <button
              onClick={() => shift(1)}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted hover:text-fg"
              aria-label="Next month"
            >
              ›
            </button>
          </div>
        }
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">
          {MONTHS[view.month]} {view.year}
        </h2>
        <p className="text-sm text-muted">
          {monthCount} {monthCount === 1 ? "post" : "posts"} this month
        </p>
      </div>

      {entries.length === 0 && !error ? (
        <Card className="mt-4 text-center">
          <p className="text-sm text-muted">
            No campaigns scheduled yet.{" "}
            <Link href={`/businesses/${id}/content`} className="text-brand hover:underline">
              Draft a campaign
            </Link>{" "}
            and its posts will appear here.
          </p>
        </Card>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <div className="min-w-[720px]">
            {/* Weekday header */}
            <div className="grid grid-cols-7 gap-px">
              {WEEKDAYS.map((w) => (
                <div
                  key={w}
                  className="px-2 py-1.5 text-center text-xs font-medium uppercase tracking-wide text-muted"
                >
                  {w}
                </div>
              ))}
            </div>
            {/* Day cells */}
            <div className="grid grid-cols-7 gap-px rounded-lg border border-border bg-border">
              {cells.map((d, i) => {
                if (d === null) {
                  return <div key={i} className="min-h-[104px] bg-bg" />;
                }
                const key = dayKey(view.year, view.month, d);
                const posts = byDay.get(key) ?? [];
                const isToday = key === todayKey;
                return (
                  <div
                    key={i}
                    onDragOver={(e) => {
                      e.preventDefault();
                      if (dragOverKey !== key) setDragOverKey(key);
                    }}
                    onDragLeave={() =>
                      setDragOverKey((k) => (k === key ? null : k))
                    }
                    onDrop={(e) => {
                      e.preventDefault();
                      const itemId = e.dataTransfer.getData("text/plain");
                      setDragOverKey(null);
                      if (itemId) reschedule(itemId, key);
                    }}
                    className={
                      "min-h-[104px] bg-bg p-1.5 transition-colors " +
                      (dragOverKey === key ? "bg-brand/10 ring-2 ring-inset ring-brand" : "")
                    }
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span
                        className={
                          "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs " +
                          (isToday ? "bg-brand font-semibold text-brand-fg" : "text-muted")
                        }
                      >
                        {d}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {posts.slice(0, 3).map((p) => (
                        <DayPost key={p.id} post={p} onSelect={setEditing} />
                      ))}
                      {posts.length > 3 && (
                        <p className="px-1 text-[11px] text-muted">
                          +{posts.length - 3} more
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      {entries.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> Proposed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-green-500" /> Scheduled
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-zinc-400" /> Skipped (no account)
          </span>
          <span className="ml-auto italic">Tip: click to edit · drag a post to reschedule.</span>
        </div>
      )}

      {editing?.content_item_id && (
        <PostEditModal
          businessId={id}
          post={{
            id: editing.content_item_id,
            title: editing.title,
            body: editing.body ?? "",
            channel: editing.channel,
          }}
          onClose={() => setEditing(null)}
          onSaved={onPostSaved}
        />
      )}
    </>
  );
}

function DayPost({
  post,
  onSelect,
}: {
  post: CampaignCalendarItem;
  onSelect: (p: CampaignCalendarItem) => void;
}) {
  const time = post.scheduled_at.slice(11, 16);
  const text = post.title || post.body || "";
  const editable = Boolean(post.content_item_id);
  const movable = post.status !== "published";
  return (
    <button
      type="button"
      onClick={() => editable && onSelect(post)}
      disabled={!editable}
      draggable={movable}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", post.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      className={
        "block w-full rounded border border-border bg-surface px-1.5 py-1 text-left transition-colors hover:border-brand disabled:hover:border-border " +
        (movable ? "cursor-grab active:cursor-grabbing" : "disabled:cursor-default")
      }
      title={
        `${CHANNEL_LABELS[post.channel] ?? post.channel} · ${post.campaign_name}\n${text}` +
        (editable ? "\n(click to edit · drag to reschedule)" : "\n(drag to reschedule)")
      }
    >
      <div className="flex items-center gap-1">
        <span
          className={
            "h-1.5 w-1.5 shrink-0 rounded-full " +
            (STATUS_DOT[post.status] ?? "bg-zinc-400")
          }
        />
        <span className="truncate text-[11px] font-medium text-fg">
          {CHANNEL_LABELS[post.channel] ?? post.channel}
        </span>
        {time && <span className="ml-auto text-[10px] text-muted">{time}</span>}
      </div>
      {text && (
        <p className="mt-0.5 line-clamp-2 text-[11px] leading-tight text-muted">
          {text}
        </p>
      )}
    </button>
  );
}
