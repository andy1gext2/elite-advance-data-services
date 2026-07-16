"use client";

import { useState } from "react";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const pad = (n: number) => String(n).padStart(2, "0");
const keyOf = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`;

function todayKey() {
  const n = new Date();
  return keyOf(n.getFullYear(), n.getMonth(), n.getDate());
}

// Add `n` days to a YYYY-MM-DD key via local date math (no timezone shift).
function addDays(iso: string, n: number) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + n);
  return keyOf(dt.getFullYear(), dt.getMonth(), dt.getDate());
}

function label(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short", month: "short", day: "numeric",
  });
}

// A month-grid start-date picker that highlights the span the campaign covers
// ([start, start + spanDays - 1]). Past dates are disabled.
export function CampaignStartCalendar({
  value,
  onChange,
  spanDays,
}: {
  value: string;
  onChange: (date: string) => void;
  spanDays: number;
}) {
  const [vy, vm] = value.split("-").map(Number);
  const [view, setView] = useState({ year: vy, month: vm - 1 });

  const today = todayKey();
  const endKey = addDays(value, spanDays - 1);

  const first = new Date(view.year, view.month, 1).getDay();
  const daysIn = new Date(view.year, view.month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < first; i++) cells.push(null);
  for (let d = 1; d <= daysIn; d++) cells.push(d);

  function shift(delta: number) {
    setView((v) => {
      const dt = new Date(v.year, v.month + delta, 1);
      return { year: dt.getFullYear(), month: dt.getMonth() };
    });
  }

  return (
    <div className="rounded-xl border border-border bg-bg p-3">
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={() => shift(-1)}
          aria-label="Previous month"
          className="rounded-md px-2 py-1 text-sm text-muted hover:text-fg"
        >
          ‹
        </button>
        <span className="text-sm font-medium">
          {MONTHS[view.month]} {view.year}
        </span>
        <button
          type="button"
          onClick={() => shift(1)}
          aria-label="Next month"
          className="rounded-md px-2 py-1 text-sm text-muted hover:text-fg"
        >
          ›
        </button>
      </div>

      <div className="grid grid-cols-7 gap-0.5 text-center text-[11px] text-muted">
        {WEEKDAYS.map((w) => (
          <div key={w} className="py-1">{w}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((d, i) => {
          if (d === null) return <div key={i} />;
          const k = keyOf(view.year, view.month, d);
          const past = k < today;
          const isStart = k === value;
          const inRange = k >= value && k <= endKey;
          return (
            <button
              key={i}
              type="button"
              disabled={past}
              onClick={() => onChange(k)}
              className={
                "h-8 rounded-md text-sm transition-colors " +
                (past
                  ? "cursor-not-allowed text-muted/40"
                  : isStart
                  ? "bg-brand font-semibold text-brand-fg"
                  : inRange
                  ? "bg-brand/15 text-brand"
                  : "text-fg hover:bg-surface")
              }
            >
              {d}
            </button>
          );
        })}
      </div>

      <p className="mt-2 text-xs text-muted">
        {spanDays === 1 ? (
          <>
            Posts on <span className="font-medium text-fg">{label(value)}</span>
          </>
        ) : (
          <>
            Campaign runs <span className="font-medium text-fg">{label(value)}</span> –{" "}
            <span className="font-medium text-fg">{label(endKey)}</span>
          </>
        )}
      </p>
    </div>
  );
}
