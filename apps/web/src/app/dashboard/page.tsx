"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Business } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { BusinessEditModal } from "@/components/BusinessEditModal";
import { Alert, Badge, Button, Card } from "@/components/ui";

export default function DashboardPage() {
  const router = useRouter();
  const { me } = useAuth();
  const [businesses, setBusinesses] = useState<Business[] | null>(null);
  const [editing, setEditing] = useState<Business | null>(null);
  const [deleting, setDeleting] = useState<Business | null>(null);

  useEffect(() => {
    api.listBusinesses().then(setBusinesses).catch(() => setBusinesses([]));
  }, []);

  function onSaved(updated: Business) {
    setBusinesses((list) =>
      (list ?? []).map((b) => (b.id === updated.id ? updated : b))
    );
  }

  function onDeleted(id: string) {
    setBusinesses((list) => (list ?? []).filter((b) => b.id !== id));
    setDeleting(null);
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Your businesses</h1>
          <p className="mt-1 text-sm text-muted">
            Each business is a separate brand workspace.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {me?.is_platform_admin && (
            <Link
              href="/admin"
              className="rounded-lg border border-border px-3 py-2 text-sm font-medium text-fg hover:bg-bg"
            >
              Platform costs
            </Link>
          )}
          <Button onClick={() => router.push("/onboarding")}>
            + New business
          </Button>
        </div>
      </div>

      <div className="mt-6">
        {businesses === null ? (
          <p className="text-muted">Loading…</p>
        ) : businesses.length === 0 ? (
          <Card className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-lg font-medium">No businesses yet</p>
            <p className="max-w-sm text-sm text-muted">
              Create your first business to start generating on-brand content.
            </p>
            <Button onClick={() => router.push("/onboarding")}>
              Create your first business
            </Button>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {businesses.map((b) => (
              <Card key={b.id} className="relative h-full transition-colors hover:border-brand">
                {/* Three-dots menu — sits above the card link, top-right corner. */}
                <CardMenu
                  onEdit={() => setEditing(b)}
                  onDelete={() => setDeleting(b)}
                />
                <Link href={`/businesses/${b.id}/content`} className="block">
                  <div className="flex items-start justify-between gap-2 pr-8">
                    <div className="flex items-center gap-3">
                      {b.logo_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={b.logo_url}
                          alt={`${b.name} logo`}
                          className="h-9 w-9 shrink-0 rounded-md border border-border object-contain"
                        />
                      )}
                      <h2 className="font-semibold">{b.name}</h2>
                    </div>
                    <Badge tone="brand">{b.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted">
                    {b.industry || "No industry set"}
                  </p>
                  {b.goals && (
                    <p className="mt-3 line-clamp-2 text-sm text-fg/80">
                      {b.goals}
                    </p>
                  )}
                  <p className="mt-4 text-sm font-medium text-brand">
                    Open workspace →
                  </p>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <BusinessEditModal
          business={editing}
          onClose={() => setEditing(null)}
          onSaved={onSaved}
        />
      )}
      {deleting && (
        <DeleteBusinessModal
          business={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={() => onDeleted(deleting.id)}
        />
      )}
    </AppShell>
  );
}

// Per-card "⋯" menu with Edit / Delete. Closes on outside-click or Escape.
function CardMenu({
  onEdit,
  onDelete,
}: {
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="absolute right-2 top-2 z-10">
      <button
        type="button"
        aria-label="Business options"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex h-8 w-8 items-center justify-center rounded-md text-lg leading-none text-muted hover:bg-bg hover:text-fg"
      >
        ⋯
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-1 w-40 overflow-hidden rounded-lg border border-border bg-surface py-1 shadow-lg"
        >
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onEdit();
            }}
            className="block w-full px-3 py-2 text-left text-sm hover:bg-bg"
          >
            Edit details
          </button>
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
            className="block w-full px-3 py-2 text-left text-sm text-red-500 hover:bg-bg"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

// Confirmation before the (irreversible, cascading) delete of a whole workspace.
function DeleteBusinessModal({
  business,
  onClose,
  onDeleted,
}: {
  business: Business;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function confirm() {
    setError("");
    setBusy(true);
    try {
      await api.deleteBusiness(business.id);
      onDeleted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onMouseDown={() => !busy && onClose()}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold">Delete “{business.name}”?</h2>
        <p className="mt-2 text-sm text-muted">
          This permanently deletes this business and everything in it — content,
          campaigns, schedules, reviews, products, and connected accounts. This
          can’t be undone.
        </p>
        <Alert>{error}</Alert>
        <div className="mt-5 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={confirm} loading={busy}>
            Delete business
          </Button>
        </div>
      </div>
    </div>
  );
}
