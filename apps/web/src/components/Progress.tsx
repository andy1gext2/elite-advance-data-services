"use client";

import { useEffect, useState } from "react";

// A thin progress bar. `percent` is 0–100; optional label sits below with the %.
export function ProgressBar({
  percent,
  label,
}: {
  percent: number;
  label?: string;
}) {
  const pct = Math.min(100, Math.max(0, percent));
  return (
    <div className="w-full">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border/60">
        <div
          className="h-full rounded-full bg-brand transition-[width] duration-200 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      {label !== undefined && (
        <p className="mt-1 text-[11px] text-muted">
          {label} {Math.round(pct)}%
        </p>
      )}
    </div>
  );
}

// Smooth, time-estimated progress for operations that don't report real progress
// (single AI requests). Ramps toward ~92% over `estMs` with ease-out, then snaps
// to 100% and resets when the operation ends. Not exact — a reassuring estimate.
export function useEstimatedProgress(active: boolean, estMs = 20000): number {
  const [pct, setPct] = useState(0);

  useEffect(() => {
    if (!active) {
      // Finished: flash to 100 (only if we were mid-run), then reset.
      setPct((p) => (p > 0 ? 100 : 0));
      const t = setTimeout(() => setPct(0), 450);
      return () => clearTimeout(t);
    }
    const start = Date.now();
    setPct(3);
    const tau = estMs * 0.5;
    const iv = setInterval(() => {
      const elapsed = Date.now() - start;
      setPct(92 * (1 - Math.exp(-elapsed / tau)));
    }, 150);
    return () => clearInterval(iv);
  }, [active, estMs]);

  return pct;
}
