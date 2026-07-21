"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { LogoMark } from "./Logo";
import { NavIcon } from "./NavIcon";
import { ThemeToggle } from "./ThemeToggle";
import { Button } from "./ui";

const NAV = [
  { seg: "dashboard", label: "Dashboard", icon: "dashboard" },
  { seg: "content", label: "Content", icon: "content" },
  { seg: "calendar", label: "Calendar", icon: "calendar" },
  { seg: "campaigns", label: "Campaigns", icon: "campaigns" },
  { seg: "schedule", label: "Schedule", icon: "schedule" },
  { seg: "reputation", label: "Reputation", icon: "reputation" },
  { seg: "products", label: "Products & Services", icon: "products" },
  { seg: "billing", label: "Billing", icon: "billing" },
];

// The command-center frame: a fixed left sidebar on desktop, a top bar + a
// horizontal scroll-nav on mobile. Enforces auth (like AppShell) and provides
// the business context, so pages render only their own content.
export function WorkspaceShell({
  businessId,
  children,
}: {
  businessId: string;
  children: React.ReactNode;
}) {
  const { me, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [bizName, setBizName] = useState("");

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  useEffect(() => {
    api.getBusiness(businessId).then((b) => setBizName(b.name)).catch(() => {});
  }, [businessId]);

  if (loading || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted">
        Loading…
      </div>
    );
  }

  const base = `/businesses/${businessId}`;
  const isActive = (seg: string) => pathname === `${base}/${seg}`;

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar (desktop) */}
      <aside className="hidden border-r border-border bg-surface lg:fixed lg:inset-y-0 lg:flex lg:w-60 lg:flex-col">
        <Link
          href="/dashboard"
          className="flex h-16 items-center gap-2 border-b border-border px-5"
        >
          <LogoMark className="h-7 w-7" />
          <span className="text-sm font-bold tracking-wide">ELITE ADVANCE</span>
        </Link>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV.map((n) => {
            const active = isActive(n.seg);
            return (
              <Link
                key={n.seg}
                href={`${base}/${n.seg}`}
                className={
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors " +
                  (active
                    ? "bg-brand/10 text-brand"
                    : "text-muted hover:bg-bg hover:text-fg")
                }
              >
                <NavIcon name={n.icon} />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="space-y-2 border-t border-border p-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-bg hover:text-fg"
          >
            ← All businesses
          </Link>
          <Link
            href="/account"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-bg hover:text-fg"
          >
            ⚙ Account settings
          </Link>
          <div className="flex items-center justify-between gap-2 px-1">
            <Link
              href="/account"
              className="min-w-0 flex-1 truncate text-xs text-muted hover:text-fg"
              title={me.user.email}
            >
              {me.user.email}
            </Link>
            <ThemeToggle />
          </div>
          <Button variant="secondary" className="w-full" onClick={logout}>
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main column */}
      <div className="min-w-0 flex-1 lg:pl-60">
        <header className="sticky top-0 z-10 border-b border-border bg-surface/80 backdrop-blur">
          <div className="flex h-14 items-center justify-between gap-3 px-4">
            <div className="flex min-w-0 items-center gap-2">
              <Link href="/dashboard" className="lg:hidden">
                <LogoMark className="h-6 w-6" />
              </Link>
              <span className="truncate text-sm font-medium">{bizName || "…"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="hidden text-xs text-muted sm:inline lg:hidden xl:inline">
                {me.user.email}
              </span>
              <span className="lg:hidden">
                <ThemeToggle />
              </span>
              <Button variant="secondary" className="lg:hidden" onClick={logout}>
                Sign out
              </Button>
            </div>
          </div>
          {/* Mobile nav */}
          <nav className="flex gap-1 overflow-x-auto border-t border-border px-2 py-1.5 lg:hidden">
            {NAV.map((n) => {
              const active = isActive(n.seg);
              return (
                <Link
                  key={n.seg}
                  href={`${base}/${n.seg}`}
                  className={
                    "shrink-0 rounded-md px-3 py-1.5 text-sm font-medium transition-colors " +
                    (active ? "bg-brand/10 text-brand" : "text-muted hover:text-fg")
                  }
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
