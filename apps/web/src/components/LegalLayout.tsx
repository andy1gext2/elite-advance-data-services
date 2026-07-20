import Link from "next/link";

// Shared wrapper for the public legal pages (privacy, terms, data deletion).
export function LegalLayout({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-bg text-fg">
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <Link href="/" className="text-sm font-semibold hover:text-brand">
            ← Elite Advance Data Services
          </Link>
          <Link href="/login" className="text-sm text-muted hover:text-fg">
            Sign in
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-muted">Last updated: {updated}</p>
        <div className="legal mt-8 space-y-6 text-sm leading-relaxed text-fg/90">
          {children}
        </div>
      </main>

      <footer className="border-t border-border px-6 py-8 text-center text-sm text-muted">
        <div className="mx-auto flex max-w-3xl flex-wrap justify-center gap-6">
          <Link href="/privacy" className="hover:text-fg">Privacy</Link>
          <Link href="/terms" className="hover:text-fg">Terms</Link>
          <Link href="/data-deletion" className="hover:text-fg">Data deletion</Link>
          <span>© 2026 Elite Advance Data Services</span>
        </div>
      </footer>
    </div>
  );
}

// A titled section within a legal page.
export function Section({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold text-fg">{heading}</h2>
      {children}
    </section>
  );
}
