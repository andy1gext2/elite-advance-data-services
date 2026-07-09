// SVG recreation of the Elite Advance Data Services mark: a hexagon holding a
// bar chart with an upward growth arrow. Uses currentColor so it tints with the
// brand token (navy in light, light-blue on dark). Swap for the official asset by
// replacing LogoMark's <svg> with the vendor SVG (keep the currentColor fills).

export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      fill="none"
      role="img"
      aria-label="Elite Advance Data Services"
    >
      {/* hexagon */}
      <path
        d="M24 3 L42 13.5 V34.5 L24 45 L6 34.5 V13.5 Z"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinejoin="round"
      />
      {/* bars */}
      <rect x="14.5" y="26" width="4" height="8" rx="1" fill="currentColor" />
      <rect x="21.5" y="19.5" width="4" height="14.5" rx="1" fill="currentColor" />
      <rect x="28.5" y="23" width="4" height="11" rx="1" fill="currentColor" />
      {/* growth arrow */}
      <path
        d="M12 32.5 L35.5 12.5"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      <path d="M28.5 11 L37.5 9.5 L35.5 18.5 Z" fill="currentColor" />
    </svg>
  );
}

export function Logo({
  className = "",
  showWordmark = true,
}: {
  className?: string;
  showWordmark?: boolean;
}) {
  return (
    <span className={"inline-flex items-center gap-2.5 " + className}>
      <LogoMark className="h-8 w-8 shrink-0 text-brand" />
      {showWordmark && (
        <span className="flex flex-col leading-none">
          <span className="text-sm font-bold tracking-wide text-fg">
            ELITE ADVANCE
          </span>
          <span className="text-[10px] font-semibold tracking-[0.22em] text-muted">
            DATA SERVICES
          </span>
        </span>
      )}
    </span>
  );
}
