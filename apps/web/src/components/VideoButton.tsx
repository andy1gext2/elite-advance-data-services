"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { VideoQuota } from "@/lib/types";
import { Button } from "@/components/ui";

// Kicks off an async video render, then polls until it's ready. Guards cost with a
// confirmation dialog that shows the tenant's remaining monthly video allowance —
// each render is a real, paid Veo generation. Reused in the Content card + modal.
export function VideoButton({
  businessId,
  itemId,
  hasVideo,
  onDone,
  onError,
}: {
  businessId: string;
  itemId: string;
  hasVideo: boolean;
  onDone: (videoUrl: string) => void;
  onError: (msg: string) => void;
}) {
  const [rendering, setRendering] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [quota, setQuota] = useState<VideoQuota | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
    },
    []
  );

  function openConfirm() {
    setQuota(null);
    setConfirming(true);
    api.videoQuota(businessId).then(setQuota).catch(() => {});
  }

  const outOfQuota =
    !!quota && !quota.unlimited && quota.remaining !== null && quota.remaining <= 0;

  async function confirmGenerate() {
    setConfirming(false);
    onError("");
    setRendering(true);
    try {
      await api.generateVideo(businessId, itemId);
    } catch (e) {
      setRendering(false);
      onError(e instanceof ApiError ? e.message : "Could not start the video");
      return;
    }

    let resolved = false;
    const stop = () => {
      resolved = true;
      if (timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
      setRendering(false);
    };
    const tick = async () => {
      try {
        const job = await api.getVideoJob(businessId, itemId);
        if (job.status === "succeeded" && job.video_url) {
          stop();
          onDone(job.video_url);
        } else if (job.status === "failed") {
          stop();
          onError(job.error || "Video generation failed");
        }
      } catch {
        // transient network error — keep polling
      }
    };

    await tick(); // immediate check (mock resolves right away)
    if (!resolved) timer.current = setInterval(tick, 4000);
  }

  return (
    <>
      <Button
        variant="ghost"
        onClick={openConfirm}
        loading={rendering}
        disabled={rendering}
        title="Generate a short AI video for this post (~1–3 min, paid)"
      >
        {rendering ? "Rendering…" : hasVideo ? "🎬 Regenerate video" : "🎬 Generate video"}
      </Button>

      {confirming && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          onMouseDown={() => setConfirming(false)}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-border bg-surface p-5 shadow-xl"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <h3 className="text-base font-semibold">Generate an AI video?</h3>
            <p className="mt-2 text-sm text-muted">
              This runs a real <span className="font-medium text-fg">paid</span> Veo
              render (~1–3 min) and counts against your monthly video allowance.
            </p>

            <div className="mt-3 rounded-lg border border-border bg-bg px-3 py-2 text-sm">
              {quota === null ? (
                <span className="text-muted">Checking your allowance…</span>
              ) : quota.unlimited ? (
                <span>Unlimited video renders on your plan.</span>
              ) : outOfQuota ? (
                <span className="text-red-500">
                  You&apos;ve used all {quota.limit} video renders this month.
                </span>
              ) : (
                <span>
                  <span className="font-semibold">{quota.remaining}</span> of{" "}
                  {quota.limit} video renders left this month.
                </span>
              )}
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
              <Button onClick={confirmGenerate} disabled={outOfQuota || quota === null}>
                Generate video
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
