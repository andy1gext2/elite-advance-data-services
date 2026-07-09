"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  CHANNEL_LABELS,
  type Business,
  type Plan,
  type PlanSlot,
  type Timeframe,
} from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { BusinessTabs } from "@/components/BusinessTabs";
import { Alert, Badge, Button, Card, Field, Textarea } from "@/components/ui";

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
  { value: "quarter", label: "Quarter" },
  { value: "year", label: "Year" },
];

// Parse a YYYY-MM-DD string into local date parts (no timezone shift).
function parseDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

const WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export default function CalendarPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [business, setBusiness] = useState<Business | null>(null);
  const [timeframe, setTimeframe] = useState<Timeframe>("month");
  const [theme, setTheme] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getBusiness(id).then(setBusiness).catch(() => {});
  }, [id]);

  async function onPlan(e: React.FormEvent) {
    e.preventDefault();
    if (!theme.trim()) return;
    setError("");
    setBusy(true);
    try {
      setPlan(await api.planCalendar(id, timeframe, theme.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Planning failed");
    } finally {
      setBusy(false);
    }
  }

  const channelCount = plan
    ? new Set(plan.slots.map((s) => s.channel)).size
    : 0;

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

      <h1 className="mt-6 text-2xl font-semibold">AI content calendar</h1>
      <p className="mt-1 text-sm text-muted">
        Give a theme and a horizon. The AI proposes what to post, on which
        platform, and when — a ready-to-fill posting schedule.
      </p>

      <Card className="mt-6">
        <form onSubmit={onPlan} className="space-y-4">
          <div>
            <span className="mb-1.5 block text-sm font-medium text-fg">
              Horizon
            </span>
            <div className="flex flex-wrap gap-2">
              {TIMEFRAMES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setTimeframe(t.value)}
                  className={
                    "rounded-lg border px-4 py-2 text-sm font-medium transition-colors " +
                    (timeframe === t.value
                      ? "border-brand bg-brand/10 text-brand"
                      : "border-border text-muted hover:text-fg")
                  }
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <Field label="Theme / campaign focus">
            <Textarea
              rows={2}
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="Fall seasonal menu — pumpkin drinks, cozy vibes, loyalty rewards."
            />
          </Field>
          <Alert>{error}</Alert>
          <div className="flex justify-end">
            <Button type="submit" loading={busy} disabled={!theme.trim()}>
              {busy ? "Planning…" : "Generate calendar"}
            </Button>
          </div>
        </form>
      </Card>

      {plan && (
        <div className="mt-8">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold capitalize">
              {plan.timeframe} plan
            </h2>
            <p className="text-sm text-muted">
              {plan.slots.length} posts across {channelCount} channels
            </p>
          </div>

          <div className="mt-4 grid gap-3">
            {plan.slots.map((slot, i) => (
              <SlotRow key={i} businessId={id} slot={slot} />
            ))}
          </div>
        </div>
      )}
    </AppShell>
  );
}

function SlotRow({ businessId, slot }: { businessId: string; slot: PlanSlot }) {
  const d = parseDate(slot.date);
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [error, setError] = useState("");

  async function schedule() {
    setError("");
    setState("busy");
    try {
      const [y, m, day] = slot.date.split("-").map(Number);
      const [hh, mm] = slot.recommended_time.split(":").map(Number);
      // Slot date + recommended local time → tz-aware ISO for correct UTC storage.
      const scheduled_at = new Date(y, m - 1, day, hh, mm).toISOString();
      await api.scheduleSlot(businessId, {
        channel: slot.channel,
        topic: slot.topic,
        scheduled_at,
      });
      setState("done");
    } catch (err) {
      setState("idle");
      setError(err instanceof ApiError ? err.message : "Could not schedule");
    }
  }

  return (
    <Card className="flex items-start gap-4 p-4">
      {/* Calendar tile */}
      <div className="flex w-14 shrink-0 flex-col items-center rounded-lg border border-border bg-bg py-1.5 text-center">
        <span className="text-[11px] font-medium uppercase text-muted">
          {WEEKDAY[d.getDay()]}
        </span>
        <span className="text-xl font-semibold leading-none">
          {d.getDate()}
        </span>
        <span className="text-[11px] text-muted">{MONTH[d.getMonth()]}</span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">
            {CHANNEL_LABELS[slot.channel] ?? slot.channel}
          </Badge>
          <span className="text-xs text-muted">⏰ {slot.recommended_time}</span>
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm text-fg/90">
          {slot.topic}
        </p>
        {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      </div>

      <div className="shrink-0">
        {state === "done" ? (
          <span className="inline-flex items-center gap-2 text-sm text-green-600 dark:text-green-500">
            ✓ Scheduled
          </span>
        ) : (
          <Button
            variant="secondary"
            loading={state === "busy"}
            onClick={schedule}
          >
            Schedule
          </Button>
        )}
      </div>
    </Card>
  );
}
