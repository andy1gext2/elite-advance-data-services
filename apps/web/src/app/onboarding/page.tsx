"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PLATFORM_LABELS } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { PlatformLogo } from "@/components/PostPreview";
import { Alert, Button, Card, Field, Input, Textarea } from "@/components/ui";

// Meta (Facebook + Instagram) and Google Business first — the platforms clients
// most want, and the ones with real OAuth connectors.
const CONNECT_PLATFORMS = [
  "facebook",
  "instagram",
  "google_business",
  "linkedin",
  "x",
  "threads",
] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const { refreshMe } = useAuth();
  const [step, setStep] = useState<"details" | "connect">("details");
  const [businessId, setBusinessId] = useState("");
  const [form, setForm] = useState({
    name: "",
    industry: "",
    website: "",
    target_audience: "",
    brand_voice: "",
    tone: "",
    goals: "",
  });
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [connecting, setConnecting] = useState("");

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function onLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setLogoFile(file);
    setLogoPreview(file ? URL.createObjectURL(file) : null);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v.trim() !== "")
      );
      const business = await api.createBusiness(payload);
      // Logo is optional and non-blocking — a failed upload shouldn't stop onboarding.
      if (logoFile) {
        try {
          await api.uploadBusinessLogo(business.id, logoFile);
        } catch {
          /* ignore — they can add it later from Edit details */
        }
      }
      await refreshMe();
      setBusinessId(business.id);
      setStep("connect");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function connect(platform: string) {
    setError("");
    setConnecting(platform);
    try {
      // Hand off to the provider's consent screen; the callback returns to the
      // workspace with the account connected.
      const { authorize_url } = await api.startOAuth(businessId, platform);
      window.location.href = authorize_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start connect");
      setConnecting("");
    }
  }

  if (step === "connect") {
    return (
      <AppShell>
        <div className="mx-auto max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-wide text-brand">
            Step 2 of 2
          </p>
          <h1 className="mt-1 text-2xl font-semibold">Connect your accounts</h1>
          <p className="mt-1 text-sm text-muted">
            Link the social accounts for <span className="font-medium text-fg">{form.name}</span>.
            The studio then generates content for exactly these platforms — and can
            publish on your behalf once connected.
          </p>

          <Alert>{error}</Alert>

          <Card className="mt-6">
            <div className="grid gap-3 sm:grid-cols-2">
              {CONNECT_PLATFORMS.map((p) => (
                <div
                  key={p}
                  className="flex items-center gap-3 rounded-lg border border-border p-3"
                >
                  <PlatformLogo channel={p} size={28} />
                  <span className="flex-1 text-sm font-medium">
                    {PLATFORM_LABELS[p] ?? p}
                  </span>
                  <Button
                    variant="secondary"
                    onClick={() => connect(p)}
                    loading={connecting === p}
                  >
                    Connect
                  </Button>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-muted">
              You&apos;ll approve access on the platform, then land back in your
              workspace. You can connect more anytime from the Schedule tab.
            </p>
          </Card>

          <div className="mt-4 flex justify-end gap-3">
            <Button
              variant="ghost"
              onClick={() => router.replace(`/businesses/${businessId}/content`)}
            >
              Skip for now
            </Button>
            <Button onClick={() => router.replace(`/businesses/${businessId}/content`)}>
              Go to workspace →
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-wide text-brand">
          Step 1 of 2
        </p>
        <h1 className="mt-1 text-2xl font-semibold">Tell us about your business</h1>
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
            <Field label="Logo" hint="Optional. PNG, JPG, WEBP, or GIF — up to 5 MB.">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-lg border border-border bg-bg">
                  {logoPreview ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={logoPreview} alt="Logo preview" className="h-full w-full object-contain" />
                  ) : (
                    <span className="text-xs text-muted">No logo</span>
                  )}
                </div>
                <label className="cursor-pointer rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-bg">
                  {logoFile ? "Change logo" : "Upload logo"}
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    onChange={onLogoChange}
                    className="hidden"
                  />
                </label>
                {logoFile && (
                  <button
                    type="button"
                    onClick={() => {
                      setLogoFile(null);
                      setLogoPreview(null);
                    }}
                    className="text-sm text-muted hover:text-fg"
                  >
                    Remove
                  </button>
                )}
              </div>
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
                Continue →
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
