"use client";

import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Asset } from "@/lib/types";
import { Alert, Button, Card, Field, Input } from "@/components/ui";

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
}

// Post a saved "Customized media" asset (the owner's exact photo/video) to all
// connected platforms on a chosen day. The AI writes the caption from the media's
// description. The media itself lives under Products & Services → Customized media.
export function CustomizedMediaCard({
  businessId,
  mediaAssets,
  onPosted,
}: {
  businessId: string;
  mediaAssets: Asset[];
  onPosted: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [assetId, setAssetId] = useState("");
  const [date, setDate] = useState(todayISO());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function post() {
    if (!assetId) return;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const items = await api.postMediaAsset(businessId, assetId, date);
      const channels = [...new Set(items.map((i) => i.channel))];
      setNotice(
        `Scheduled to ${channels.length} platform${channels.length === 1 ? "" : "s"} ` +
          `(${channels.join(", ")}) for ${date}, with an AI-written caption. See the Schedule tab.`
      );
      onPosted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not post");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <div>
          <h2 className="text-lg font-semibold">Post customized media</h2>
          <p className="mt-1 text-sm text-muted">
            Post one of your own photos/videos exactly as-is to all connected
            platforms on a day you pick — the AI writes the caption.
          </p>
        </div>
        <span className="shrink-0 text-muted">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          {mediaAssets.length === 0 ? (
            <p className="text-sm text-muted">
              No customized media yet. Add one under{" "}
              <Link
                href={`/businesses/${businessId}/products`}
                className="text-brand hover:underline"
              >
                Products &amp; Services → Customized media
              </Link>
              .
            </p>
          ) : (
            <>
              <Field label="Choose media">
                <select
                  value={assetId}
                  onChange={(e) => setAssetId(e.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
                >
                  <option value="">Select a saved media…</option>
                  {mediaAssets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {(a.content_type ?? "").startsWith("video/") ? "🎬 " : "🖼 "}
                      {a.name ?? a.filename}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Post date" hint="Posts to every connected platform on this day.">
                <Input
                  type="date"
                  value={date}
                  min={todayISO()}
                  onChange={(e) => setDate(e.target.value)}
                />
              </Field>

              {notice && (
                <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">
                  {notice}
                </p>
              )}
              <Alert>{error}</Alert>

              <div className="flex justify-end">
                <Button onClick={post} loading={busy} disabled={!assetId}>
                  Post to all connected platforms
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
