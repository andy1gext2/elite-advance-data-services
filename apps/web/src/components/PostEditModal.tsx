"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { CHANNEL_LABELS, type Asset, type ContentItem } from "@/lib/types";
import { PostPreview } from "@/components/PostPreview";
import { VideoButton } from "@/components/VideoButton";
import { Button, Field, Input, Textarea } from "@/components/ui";

// The single post editor reused across Content, Campaigns, and Calendar. Edits a
// content item's copy (title/body) and its image (regenerate, optionally grounded
// on a product). Every save/regenerate reports the updated item via onSaved so the
// caller can refresh its own view.
export type EditablePost = {
  id: string; // content_item_id
  title: string | null;
  body: string;
  channel: string;
  content_type?: string;
  image_url?: string | null;
  video_url?: string | null;
};

export function PostEditModal({
  businessId,
  post,
  businessName = "Your brand",
  assets = [],
  defaultProductId = "",
  onClose,
  onSaved,
}: {
  businessId: string;
  post: EditablePost;
  businessName?: string;
  assets?: Asset[];
  defaultProductId?: string;
  onClose: () => void;
  onSaved: (updated: ContentItem) => void;
}) {
  const [title, setTitle] = useState(post.title ?? "");
  const [body, setBody] = useState(post.body);
  const [imageUrl, setImageUrl] = useState<string | null>(post.image_url ?? null);
  const [videoUrl, setVideoUrl] = useState<string | null>(post.video_url ?? null);
  const [productId, setProductId] = useState(defaultProductId);
  const [saving, setSaving] = useState(false);
  const [imaging, setImaging] = useState(false);
  const [error, setError] = useState("");

  const close = useCallback(() => {
    if (!saving && !imaging) onClose();
  }, [saving, imaging, onClose]);

  // Close on Escape.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  async function regenerate() {
    setError("");
    setImaging(true);
    try {
      const updated = await api.generateImage(businessId, post.id, productId || undefined);
      setImageUrl(updated.image_url ?? null);
      onSaved(updated); // image is persisted immediately, so reflect it upstream
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Image generation failed");
    } finally {
      setImaging(false);
    }
  }

  async function save() {
    if (!body.trim()) return;
    setError("");
    setSaving(true);
    try {
      const updated = await api.updateContent(businessId, post.id, {
        title: title.trim() || null,
        body,
      });
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm sm:p-8"
      onMouseDown={close}
    >
      <div
        className="my-auto w-full max-w-3xl rounded-2xl border border-border bg-surface shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold">
            Edit {CHANNEL_LABELS[post.channel] ?? post.channel} post
          </h2>
          <button
            onClick={close}
            aria-label="Close"
            className="rounded-md px-2 text-xl leading-none text-muted hover:text-fg"
          >
            ×
          </button>
        </div>

        <div className="grid gap-5 p-5 md:grid-cols-2">
          {/* Editable copy */}
          <div className="space-y-3">
            <Field label="Title">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Optional"
              />
            </Field>
            <Field label="Body">
              <Textarea rows={10} value={body} onChange={(e) => setBody(e.target.value)} />
            </Field>
          </div>

          {/* Preview + image controls */}
          <div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">
                Preview
              </p>
              <div className="flex items-center gap-2">
                {assets.length > 0 && (
                  <select
                    value={productId}
                    onChange={(e) => setProductId(e.target.value)}
                    title="Base the image on a product photo"
                    className="max-w-[130px] rounded-lg border border-border bg-bg px-2 py-1.5 text-xs text-fg outline-none focus:border-brand"
                  >
                    <option value="">No product</option>
                    {assets.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name ?? a.filename}
                      </option>
                    ))}
                  </select>
                )}
                <Button variant="ghost" onClick={regenerate} loading={imaging}>
                  {imageUrl ? "🖼 Regenerate" : "🖼 Generate image"}
                </Button>
                <VideoButton
                  businessId={businessId}
                  itemId={post.id}
                  hasVideo={Boolean(videoUrl)}
                  onDone={setVideoUrl}
                  onError={setError}
                />
              </div>
            </div>
            <PostPreview
              channel={post.channel}
              body={body}
              business={businessName}
              isVideo={post.content_type === "video_script"}
              imageUrl={imageUrl}
              videoUrl={videoUrl}
            />
          </div>
        </div>

        {error && (
          <p className="px-5 text-sm text-red-500">{error}</p>
        )}

        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <Button variant="ghost" onClick={close} disabled={saving || imaging}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving} disabled={!body.trim()}>
            Save changes
          </Button>
        </div>
      </div>
    </div>
  );
}
