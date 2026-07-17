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
  script,
}: {
  businessId: string;
  itemId: string;
  hasVideo: boolean;
  onDone: (videoUrl: string) => void;
  onError: (msg: string) => void;
  // When provided, the parent owns the vision editor (e.g. the Edit modal) and
  // this render uses that text — the button hides its own built-in editor.
  script?: string;
}) {
  const [rendering, setRendering] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [quota, setQuota] = useState<VideoQuota | null>(null);
  const [buying, setBuying] = useState(false);
  const [vision, setVision] = useState("");
  const [loadingVision, setLoadingVision] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
    },
    []
  );

  function openConfirm() {
    setQuota(null);
    setVision("");
    setConfirming(true);
    api.videoQuota(businessId).then(setQuota).catch(() => {});
  }

  // Ask Claude to write the 8-second vision so the owner can see + edit it before rendering.
  async function loadVision() {
    setLoadingVision(true);
    onError("");
    try {
      const { prompt } = await api.generateVideoScript(businessId, itemId);
      setVision(prompt);
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Could not write the vision");
    } finally {
      setLoadingVision(false);
    }
  }

  const monthlyLeft =
    quota && !quota.unlimited && quota.remaining !== null ? quota.remaining : Infinity;
  const credits = quota?.credits ?? 0;
  // Blocked only when both the monthly allowance AND credits are used up.
  const blocked = !!quota && !quota.unlimited && monthlyLeft <= 0 && credits <= 0;
  const usesCredit = !!quota && !quota.unlimited && monthlyLeft <= 0 && credits > 0;

  async function buyCredits() {
    setBuying(true);
    try {
      // Live billing -> Stripe checkout; dev (no Stripe) -> grants directly.
      const { url } = await api.billingCreditsCheckout(businessId);
      if (url) {
        window.location.href = url;
        return;
      }
      setQuota(await api.videoQuota(businessId));
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Could not add credits");
    } finally {
      setBuying(false);
    }
  }

  async function confirmGenerate() {
    setConfirming(false);
    onError("");
    setRendering(true);
    // Parent-supplied vision wins; otherwise use this button's own editor.
    const finalVision = (script ?? vision).trim();
    try {
      await api.generateVideo(businessId, itemId, finalVision || undefined);
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
              ) : blocked ? (
                <span className="text-red-500">
                  You&apos;ve used all {quota.limit} monthly renders and have no credits.
                </span>
              ) : usesCredit ? (
                <span>
                  No monthly renders left — this uses{" "}
                  <span className="font-semibold">1</span> of your {credits} credits.
                </span>
              ) : (
                <span>
                  <span className="font-semibold">{quota.remaining}</span> of {quota.limit}{" "}
                  monthly renders left
                  {credits > 0 && <> · {credits} credits</>}.
                </span>
              )}
            </div>

            {/* The 8-second vision Claude will hand to Veo — preview and edit it.
                Hidden when the parent (Edit modal) already owns a vision editor. */}
            {script !== undefined ? (
              script.trim() ? (
                <p className="mt-3 text-xs text-muted">
                  Rendering your edited 8-second vision.
                </p>
              ) : null
            ) : (
            <div className="mt-3">
              {vision ? (
                <>
                  <label className="text-xs font-medium text-muted">
                    🎬 The 8-second vision (edit to steer the render)
                  </label>
                  <textarea
                    value={vision}
                    onChange={(e) => setVision(e.target.value)}
                    rows={5}
                    maxLength={4000}
                    className="mt-1 w-full resize-y rounded-lg border border-border bg-bg px-3 py-2 text-sm leading-relaxed outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
                    placeholder="Describe the 8-second shot…"
                  />
                  <button
                    type="button"
                    onClick={loadVision}
                    disabled={loadingVision}
                    className="mt-1 text-xs text-brand hover:underline disabled:opacity-50"
                  >
                    {loadingVision ? "Rewriting…" : "↻ Let Claude rewrite it"}
                  </button>
                </>
              ) : (
                <Button
                  variant="secondary"
                  onClick={loadVision}
                  loading={loadingVision}
                  className="w-full"
                >
                  ✨ Preview &amp; edit the 8-second vision
                </Button>
              )}
            </div>
            )}

            <div className="mt-4 flex items-center justify-end gap-2">
              {blocked && (
                <Button variant="secondary" onClick={buyCredits} loading={buying}>
                  Buy 10 renders
                </Button>
              )}
              <Button variant="ghost" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
              <Button onClick={confirmGenerate} disabled={blocked || quota === null}>
                Generate video
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
