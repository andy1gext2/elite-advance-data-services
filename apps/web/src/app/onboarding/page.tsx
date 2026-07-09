"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/AppShell";
import { Alert, Button, Card, Field, Input, Textarea } from "@/components/ui";

export default function OnboardingPage() {
  const router = useRouter();
  const { refreshMe } = useAuth();
  const [form, setForm] = useState({
    name: "",
    industry: "",
    website: "",
    target_audience: "",
    brand_voice: "",
    tone: "",
    goals: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      // Strip empties so the backend keeps its defaults.
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v.trim() !== "")
      );
      const business = await api.createBusiness(payload);
      await refreshMe();
      router.replace(`/businesses/${business.id}/content`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-semibold">Tell us about your business</h1>
        <p className="mt-1 text-sm text-muted">
          This is the brand context the AI uses to write on your behalf. You can
          refine it later.
        </p>

        <Card className="mt-6">
          <form onSubmit={onSubmit} className="space-y-4">
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
              <Button
                type="button"
                variant="ghost"
                onClick={() => router.push("/dashboard")}
              >
                Cancel
              </Button>
              <Button type="submit" loading={busy}>
                Create business
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
