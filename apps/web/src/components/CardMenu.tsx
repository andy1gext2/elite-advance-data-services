"use client";

import { useEffect, useRef, useState } from "react";

// A reusable "⋯" dropdown menu for cards/rows. Closes on outside-click or Escape.
export function CardMenu({
  items,
}: {
  items: { label: string; onClick: () => void; danger?: boolean }[];
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
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Options"
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
          className="absolute right-0 z-20 mt-1 w-36 overflow-hidden rounded-lg border border-border bg-surface py-1 shadow-lg"
        >
          {items.map((it, i) => (
            <button
              key={i}
              role="menuitem"
              onClick={() => {
                setOpen(false);
                it.onClick();
              }}
              className={
                "block w-full px-3 py-2 text-left text-sm hover:bg-bg " +
                (it.danger ? "text-red-500" : "")
              }
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
