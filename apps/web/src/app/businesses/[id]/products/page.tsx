"use client";

/* eslint-disable @next/next/no-img-element */
import { use, useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Asset } from "@/lib/types";
import { Alert, Button, Card, Field, Input, PageHeader, Textarea } from "@/components/ui";

export default function ProductsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [error, setError] = useState("");

  // New-product form.
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setAssets(await api.listAssets(id));
  }, [id]);

  useEffect(() => {
    load().catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, [load]);

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      await api.uploadAsset(id, file, {
        name: name.trim() || undefined,
        description: description.trim() || undefined,
      });
      setName("");
      setDescription("");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed");
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

  return (
    <>
      <PageHeader
        title="Products"
        subtitle="Upload each product with a short description. The AI uses the photo as a baseline for visuals and the description as its navigator when writing campaigns — so posts promote what you actually sell."
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      <Card className="mt-6">
        <form onSubmit={onUpload} className="grid gap-4 md:grid-cols-2">
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
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  className="h-28 w-28 rounded-lg object-cover"
                />
                <span className="text-xs text-muted">{file.name} · click to change</span>
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
            <Field label="Product name">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ethiopia Single-Origin Beans"
              />
            </Field>
            <Field label="Short description (the AI's navigator)">
              <Textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Bright, citrusy light roast. Ethically sourced, small-batch. Best as pour-over. $18 / 12oz."
              />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" loading={uploading} disabled={!file}>
                {uploading ? "Uploading…" : "Add product"}
              </Button>
            </div>
          </div>
        </form>
      </Card>

      <h2 className="mt-8 text-lg font-semibold">
        Product library <span className="text-muted">({assets.length})</span>
      </h2>
      {assets.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          No products yet — add a few so the AI can build campaigns around them.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {assets.map((a) => (
            <Card key={a.id} className="flex gap-3 p-3">
              <img
                src={a.url}
                alt={a.name ?? a.filename}
                className="h-20 w-20 shrink-0 rounded-lg object-cover"
              />
              <div className="flex min-w-0 flex-1 flex-col">
                <p className="truncate text-sm font-medium">
                  {a.name ?? a.filename}
                </p>
                {a.description ? (
                  <p className="mt-0.5 line-clamp-3 text-xs text-muted">
                    {a.description}
                  </p>
                ) : (
                  <p className="mt-0.5 text-xs italic text-muted">
                    No description — add one so the AI knows what to say.
                  </p>
                )}
                <button
                  onClick={() => remove(a.id)}
                  className="mt-auto self-start pt-2 text-xs text-red-500 hover:underline"
                >
                  Delete
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
