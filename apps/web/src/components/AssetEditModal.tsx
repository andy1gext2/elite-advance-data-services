"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Asset } from "@/lib/types";
import { Alert, Button, Field, Input, Textarea } from "@/components/ui";

// Edit a product/service: name, description, and optionally replace its photo.
export function AssetEditModal({
  businessId,
  asset,
  onClose,
  onSaved,
}: {
  businessId: string;
  asset: Asset;
  onClose: () => void;
  onSaved: (updated: Asset) => void;
}) {
  const isService = asset.kind === "service";
  const [name, setName] = useState(asset.name ?? asset.filename ?? "");
  const [description, setDescription] = useState(asset.description ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(asset.url ?? null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const close = useCallback(() => {
    if (!saving) onClose();
  }, [saving, onClose]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (f) setPreview(URL.createObjectURL(f));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const updated = await api.updateAsset(businessId, asset.id, {
        name: name.trim(),
        description: description.trim(),
        file,
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
        className="my-auto w-full max-w-lg rounded-2xl border border-border bg-surface shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold">
            Edit {isService ? "service" : "product"}
          </h2>
          <button
            onClick={close}
            aria-label="Close"
            className="rounded-md px-2 text-xl leading-none text-muted hover:text-fg"
          >
            ×
          </button>
        </div>

        <form onSubmit={save} className="space-y-4 p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-bg">
              {preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt={name} className="h-full w-full object-cover" />
              ) : (
                <span className="text-2xl">{isService ? "🛠" : "📦"}</span>
              )}
            </div>
            <label className="cursor-pointer rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-bg">
              {preview ? "Replace photo" : "Add photo"}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                onChange={onFileChange}
                className="hidden"
              />
            </label>
          </div>

          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field
            label="Description"
            hint="The AI uses this to know what to say about it."
          >
            <Textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What it is, who it's for, what makes it special…"
            />
          </Field>

          <Alert>{error}</Alert>

          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={close}>
              Cancel
            </Button>
            <Button type="submit" loading={saving}>
              Save changes
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
