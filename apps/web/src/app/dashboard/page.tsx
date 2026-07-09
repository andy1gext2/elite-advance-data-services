"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Business } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { Badge, Button, Card } from "@/components/ui";

export default function DashboardPage() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState<Business[] | null>(null);

  useEffect(() => {
    api.listBusinesses().then(setBusinesses).catch(() => setBusinesses([]));
  }, []);

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Your businesses</h1>
          <p className="mt-1 text-sm text-muted">
            Each business is a separate brand workspace.
          </p>
        </div>
        <Button onClick={() => router.push("/onboarding")}>
          + New business
        </Button>
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
              <Link key={b.id} href={`/businesses/${b.id}/content`}>
                <Card className="h-full transition-colors hover:border-brand">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-semibold">{b.name}</h2>
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
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
