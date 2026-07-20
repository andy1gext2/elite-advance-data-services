"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Alert, Button, Card, Field, Textarea } from "@/components/ui";

// "Post your own media" — upload a photo or video and publish it exactly as-is to
// every connected platform, scheduled 1 day out. No AI, no campaign (a single
// asset would just repeat across a campaign).
export function UploadMediaCard({
  businessId,
  onPosted,
}: {
  businessId: string;
  onPosted: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isVideo, setIsVideo] = useState(false);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setIsVideo(!!f && f.type.startsWith("video/"));
    setPreview(f ? URL.createObjectURL(f) : null);
    setNotice("");
    setError("");
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setCaption("");
  }

  async function post() {
    if (!file) return;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const items = await api.uploadContentMedia(businessId, file, caption.trim() || undefined);
      const channels = [...new Set(items.map((i) => i.channel))];
      setNotice(
        `Scheduled to post to ${channels.length} platform${channels.length === 1 ? "" : "s"} ` +
          `(${channels.join(", ")}) — going out in 1 day. See the Schedule tab.`
      );
      reset();
      onPosted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
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
          <h2 className="text-lg font-semibold">Post your own media</h2>
          <p className="mt-1 text-sm text-muted">
            Upload a photo or video and post it exactly as-is to all your connected
            platforms — scheduled 1 day out.
          </p>
        </div>
        <span className="shrink-0 text-muted">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
      <div className="mt-4 space-y-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-lg border border-border bg-bg">
            {preview ? (
              isVideo ? (
                <video src={preview} className="h-full w-full object-cover" muted />
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt="Preview" className="h-full w-full object-cover" />
              )
            ) : (
              <span className="px-2 text-center text-xs text-muted">Photo or video</span>
            )}
          </div>
          <label className="cursor-pointer rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-bg">
            {file ? "Change file" : "Choose photo / video"}
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif,video/mp4,video/quicktime,video/webm"
              onChange={onFileChange}
              className="hidden"
            />
          </label>
          {file && (
            <span className="text-sm text-muted">
              {file.name} {isVideo ? "(video)" : "(photo)"}
            </span>
          )}
        </div>

        <Field label="Caption" hint="Optional — used on every platform.">
          <Textarea
            rows={2}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Write a caption to go with your media…"
          />
        </Field>

        {notice && (
          <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600 dark:text-emerald-400">
            {notice}
          </p>
        )}
        <Alert>{error}</Alert>

        <div className="flex justify-end">
          <Button onClick={post} loading={busy} disabled={!file}>
            {busy ? "Scheduling…" : "Post to all connected platforms"}
          </Button>
        </div>
      </div>
      )}
    </Card>
  );
}
