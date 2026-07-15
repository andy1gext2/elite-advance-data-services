/* eslint-disable @next/next/no-img-element */
// The real Elite Advance Data Services logo (processed from the brand asset into
// transparent, theme-aware PNGs). Navy renders in light mode, white in dark mode —
// the swap is pure CSS (dark: variants), so there's no flash.

export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <span className={`relative inline-block ${className}`}>
      <img
        src="/logo-mark.png"
        alt="Elite Advance Data Services"
        className="h-full w-full object-contain dark:hidden"
      />
      <img
        src="/logo-mark-white.png"
        alt=""
        aria-hidden="true"
        className="hidden h-full w-full object-contain dark:block"
      />
    </span>
  );
}

// Horizontal lockup for nav bars: the exact mark + the wordmark.
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark className="h-8 w-8 shrink-0" />
      <span className="flex flex-col leading-none">
        <span className="text-sm font-semibold tracking-tight text-fg">
          Elite Advance
        </span>
        <span className="text-[10px] font-medium tracking-[0.18em] text-muted">
          DATA SERVICES
        </span>
      </span>
    </span>
  );
}

// The full stacked lockup (exact brand asset) for auth pages / footer.
export function LogoLockup({ className = "h-20" }: { className?: string }) {
  return (
    <span className={`inline-block ${className}`}>
      <img
        src="/logo.png"
        alt="Elite Advance Data Services"
        className="h-full w-auto object-contain dark:hidden"
      />
      <img
        src="/logo-white.png"
        alt=""
        aria-hidden="true"
        className="hidden h-full w-auto object-contain dark:block"
      />
    </span>
  );
}
