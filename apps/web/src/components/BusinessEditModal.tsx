"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Business } from "@/lib/types";
import { Alert, Button, Field, Input, Textarea } from "@/components/ui";

// Edits a business's brand/profile — the same details captured during onboarding
// (name, industry, website, audience, voice, tone, goals). Saves via PATCH and
// reports the updated business through onSaved so the caller can refresh.
export function BusinessEditModal({
  business,
  onClose,
  onSaved,
}: {
  business: Business;
  onClose: () => void;
  onSaved: (updated: Business) => void;
}) {
  const [form, setForm] = useState({
    name: business.name ?? "",
    industry: business.industry ?? "",
    website: business.website ?? "",
    target_audience: business.target_audience ?? "",
    brand_voice: business.brand_voice ?? "",
    tone: business.tone ?? "",
    goals: business.goals ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

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

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("Business name is required");
      return;
    }
    setError("");
    setSaving(true);
    try {
      // Send trimmed values; blank optional fields clear to null (matching onboarding).
      const updated = await api.updateBusiness(business.id, {
        name: form.name.trim(),
        industry: form.industry.trim() || null,
        website: form.website.trim() || null,
        target_audience: form.target_audience.trim() || null,
        brand_voice: form.brand_voice.trim() || null,
        tone: form.tone.trim() || null,
        goals: form.goals.trim() || null,
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
        className="my-auto w-full max-w-2xl rounded-2xl border border-border bg-surface shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold">Edit business details</h2>
          <button
            onClick={close}
            aria-label="Close"
            className="rounded-md px-2 text-xl leading-none text-muted hover:text-fg"
          >
            ×
          </button>
        </div>

        <form onSubmit={save} className="space-y-4 p-5">
          <Field label="Business name">
            <Input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Acme Coffee Co."
              required
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Industry">
              <Input
                value={form.industry}
                onChange={(e) => set("industry", e.target.value)}
                placeholder="Food & beverage"
              />
            </Field>
            <Field label="Website">
              <Input
                value={form.website}
                onChange={(e) => set("website", e.target.value)}
                placeholder="https://acme.coffee"
              />
            </Field>
          </div>
          <Field label="Target audience">
            <Textarea
              rows={2}
              value={form.target_audience}
              onChange={(e) => set("target_audience", e.target.value)}
              placeholder="Local professionals, 25–45, who value quality and speed."
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Brand voice">
              <Input
                value={form.brand_voice}
                onChange={(e) => set("brand_voice", e.target.value)}
                placeholder="Warm, witty, confident"
              />
            </Field>
            <Field label="Tone">
              <Input
                value={form.tone}
                onChange={(e) => set("tone", e.target.value)}
                placeholder="Friendly"
              />
            </Field>
          </div>
          <Field label="Goals">
            <Textarea
              rows={2}
              value={form.goals}
              onChange={(e) => set("goals", e.target.value)}
              placeholder="Grow foot traffic and build a loyal online community."
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
