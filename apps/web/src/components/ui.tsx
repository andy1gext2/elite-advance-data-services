"use client";

import { forwardRef } from "react";

function cx(...parts: Array<string | false | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx(
        "rounded-xl border border-border bg-surface p-6 shadow-sm",
        className
      )}
      {...props}
    />
  );
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", loading, disabled, children, ...props }, ref) => {
    const styles: Record<string, string> = {
      primary:
        "bg-brand text-brand-fg hover:opacity-90 disabled:opacity-50",
      secondary:
        "border border-border bg-surface text-fg hover:bg-bg disabled:opacity-50",
      ghost: "text-fg/80 hover:bg-surface disabled:opacity-50",
      danger:
        "border border-red-500/40 text-red-500 hover:bg-red-500/10 disabled:opacity-50",
    };
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cx(
          "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
          styles[variant],
          className
        )}
        {...props}
      >
        {loading && (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export const Input = forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cx(
      "w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg placeholder:text-muted outline-none focus:border-brand focus:ring-2 focus:ring-brand/30",
      className
    )}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cx(
      "w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg placeholder:text-muted outline-none focus:border-brand focus:ring-2 focus:ring-brand/30",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-fg">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "green" | "red" | "amber" | "brand";
}) {
  const tones: Record<string, string> = {
    default: "bg-bg text-muted border-border",
    green: "bg-green-500/10 text-green-500 border-green-500/30",
    red: "bg-red-500/10 text-red-500 border-red-500/30",
    amber: "bg-amber-500/10 text-amber-600 border-amber-500/30",
    brand: "bg-brand/10 text-brand border-brand/30",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
        tones[tone]
      )}
    >
      {children}
    </span>
  );
}

// Consistent page top used across the workspace: title, optional subtitle, and
// an optional right-aligned action (e.g. a primary button).
export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Alert({ children }: { children: React.ReactNode }) {
  if (!children) return null;
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-500">
      {children}
    </div>
  );
}
