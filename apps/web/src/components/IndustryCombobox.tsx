"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Industry } from "@/lib/types";
import { Input } from "@/components/ui";

// Searchable industry picker: curated list (drives per-industry trend caching)
// with free-text fallback for niche businesses. The value is always the plain
// string the owner ends up with — picking an option fills the label, but they can
// type anything. Mirrors the /industries endpoint.

// Module-level cache so the list is fetched once per session.
let _cache: Industry[] | null = null;

export function IndustryCombobox({
  value,
  onChange,
  placeholder = "Start typing or pick one…",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [items, setItems] = useState<Industry[]>(_cache ?? []);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (_cache) return;
    api
      .getIndustries()
      .then((r) => {
        _cache = r.industries;
        setItems(r.industries);
      })
      .catch(() => setItems([]));
  }, []);

  // Close when clicking outside.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const q = value.trim().toLowerCase();
  const matches = (q
    ? items.filter((i) => i.label.toLowerCase().includes(q) || i.slug.includes(q))
    : items
  ).slice(0, 8);

  return (
    <div ref={wrapRef} className="relative">
      <Input
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        autoComplete="off"
      />
      {open && matches.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-border bg-surface py-1 shadow-lg">
          {matches.map((i) => (
            <li key={i.slug}>
              <button
                type="button"
                onClick={() => {
                  onChange(i.label);
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-bg"
              >
                <span aria-hidden>{i.emoji}</span>
                <span>{i.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
