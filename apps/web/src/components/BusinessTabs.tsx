"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function cx(...parts: Array<string | false | undefined>) {
  return parts.filter(Boolean).join(" ");
}

// Sub-navigation within a single business workspace.
export function BusinessTabs({ businessId }: { businessId: string }) {
  const pathname = usePathname();
  const base = `/businesses/${businessId}`;
  const tabs = [
    { href: `${base}/dashboard`, label: "Dashboard" },
    { href: `${base}/content`, label: "Content" },
    { href: `${base}/calendar`, label: "Calendar" },
    { href: `${base}/schedule`, label: "Schedule" },
    { href: `${base}/reputation`, label: "Reputation" },
  ];

  return (
    <nav className="mt-4 flex gap-1 border-b border-border">
      {tabs.map((t) => {
        const active = pathname === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            className={cx(
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              active
                ? "border-brand text-brand"
                : "border-transparent text-muted hover:text-fg"
            )}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
