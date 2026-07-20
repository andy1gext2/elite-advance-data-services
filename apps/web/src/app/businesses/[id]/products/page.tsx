"use client";

/* eslint-disable @next/next/no-img-element */
import { use, useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Asset } from "@/lib/types";
import { Alert, Button, Card, Field, Input, PageHeader, Textarea } from "@/components/ui";
import { CardMenu } from "@/components/CardMenu";
import { AssetEditModal } from "@/components/AssetEditModal";

type Kind = "product" | "service";

export default function ProductsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [error, setError] = useState("");

  // New-entry form.
  const [kind, setKind] = useState<Kind>("product");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [flyerBusy, setFlyerBusy] = useState<string | null>(null); // asset id being rendered
  const fileRef = useRef<HTMLInputElement>(null);

  const isService = kind === "service";

  const load = useCallback(async () => {
    setAssets(await api.listAssets(id));
  }, [id]);

  useEffect(() => {
    load().catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, [load]);

  function resetForm() {
    setName("");
    setDescription("");
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Products need a photo; services need at least a name or description.
    if (!isService && !file) return;
    if (isService && !name.trim() && !description.trim()) return;
    setError("");
    setUploading(true);
    try {
      await api.uploadAsset(id, file, {
        kind,
        name: name.trim() || undefined,
        description: description.trim() || undefined,
      });
      resetForm();
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Save failed");
    } finally {
      setUploading(false);
    }
  }

  async function remove(assetId: string) {
    try {
      await api.deleteAsset(id, assetId);
      setAssets((list) => list.filter((a) => a.id !== assetId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Delete failed");
    }
  }

  // Have the AI design a flyer/poster for a service, saved onto the asset.
  async function makeFlyer(assetId: string) {
    setError("");
    setFlyerBusy(assetId);
    try {
      const updated = await api.generateFlyer(id, assetId);
      setAssets((list) => list.map((a) => (a.id === assetId ? updated : a)));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Flyer generation failed");
    } finally {
      setFlyerBusy(null);
    }
  }

  const canSubmit = isService
    ? Boolean(name.trim() || description.trim())
    : Boolean(file);

  return (
    <>
      <PageHeader
        title="Products & Services"
        subtitle="Add what you sell. The AI uses the name + description as its navigator when writing campaigns, so posts promote what you actually offer. Products ground the visuals in your photo; services get an AI-designed promotional poster."
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      <Card className="mt-6">
        {/* Product / Service toggle */}
        <div className="mb-5 inline-flex rounded-xl border border-border bg-bg p-1">
          {(["product", "service"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
                kind === k ? "bg-brand text-brand-fg" : "text-muted hover:text-fg"
              }`}
            >
              {k === "product" ? "📦 Product" : "🛠 Service"}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-2">
          {/* Image picker / dropzone */}
          <label
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border py-8 text-center transition-colors hover:border-brand"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
          >
            {file ? (
              <>
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  className="h-28 w-28 rounded-lg object-cover"
                />
                <span className="text-xs text-muted">{file.name} · click to change</span>
              </>
            ) : isService ? (
              <>
                <span className="text-3xl">🎨</span>
                <span className="text-sm font-medium">
                  Optional photo — or skip it
                </span>
                <span className="text-xs text-muted">
                  Save the service, then hit ✨ Generate flyer on its card to have AI
                  design the poster from your description.
                </span>
              </>
            ) : (
              <>
                <span className="text-3xl">📦</span>
                <span className="text-sm font-medium">Drop a product photo, or click to browse</span>
                <span className="text-xs text-muted">PNG, JPEG, WebP, or GIF · up to 10 MB</span>
              </>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>

          {/* Details */}
          <div className="space-y-4">
            <Field label={isService ? "Service name" : "Product name"}>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={
                  isService
                    ? "Same-Day Gutter Cleaning"
                    : "Ethiopia Single-Origin Beans"
                }
              />
            </Field>
            <Field
              label={
                isService
                  ? "Describe your service (the AI's navigator)"
                  : "Short description (the AI's navigator)"
              }
            >
              <Textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={
                  isService
                    ? "Full-home gutter clearing, downspout flush, and roofline inspection. Licensed & insured. Flat $149, same-week booking."
                    : "Bright, citrusy light roast. Ethically sourced, small-batch. Best as pour-over. $18 / 12oz."
                }
              />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" loading={uploading} disabled={!canSubmit}>
                {uploading
                  ? "Saving…"
                  : isService
                    ? "Add service"
                    : "Add product"}
              </Button>
            </div>
          </div>
        </form>
      </Card>

      <h2 className="mt-8 text-lg font-semibold">
        Library <span className="text-muted">({assets.length})</span>
      </h2>
      {assets.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          Nothing yet — add a few products or services so the AI can build campaigns around them.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {assets.map((a) => {
            const isSvc = a.kind === "service";
            return (
            <Card key={a.id} className="relative flex gap-3 p-3">
              <div className="absolute right-2 top-2">
                <CardMenu
                  items={[
                    { label: "Edit", onClick: () => setEditing(a) },
                    { label: "Delete", danger: true, onClick: () => remove(a.id) },
                  ]}
                />
              </div>
              {a.url ? (
                <img
                  src={a.url}
                  alt={a.name ?? a.filename}
                  className="h-20 w-20 shrink-0 rounded-lg object-cover"
                />
              ) : (
                <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-lg bg-bg text-2xl">
                  {isSvc ? "🛠" : "📦"}
                </div>
              )}
              <div className="flex min-w-0 flex-1 flex-col">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium">
                    {a.name ?? a.filename}
                  </p>
                  <span className="shrink-0 rounded-full border border-border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                    {isSvc ? "Service" : "Product"}
                  </span>
                </div>
                {a.description ? (
                  <p className="mt-0.5 line-clamp-2 text-xs text-muted">
                    {a.description}
                  </p>
                ) : (
                  <p className="mt-0.5 text-xs italic text-muted">
                    No description — add one so the AI knows what to say.
                  </p>
                )}

                {/* Services get an AI flyer that gets reused across campaign posts. */}
                {isSvc && (
                  <>
                    <Button
                      variant="secondary"
                      onClick={() => makeFlyer(a.id)}
                      loading={flyerBusy === a.id}
                      className="mt-2 self-start !px-2.5 !py-1 text-xs"
                    >
                      {a.url ? "↻ Regenerate flyer" : "✨ Generate flyer with AI"}
                    </Button>
                    {a.url && (
                      <p className="mt-1 text-[11px] text-muted">
                        Reused on every post when this service runs a campaign.
                      </p>
                    )}
                  </>
                )}

              </div>
            </Card>
            );
          })}
        </div>
      )}

      {editing && (
        <AssetEditModal
          businessId={id}
          asset={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) =>
            setAssets((list) => list.map((a) => (a.id === updated.id ? updated : a)))
          }
        />
      )}
    </>
  );
}
