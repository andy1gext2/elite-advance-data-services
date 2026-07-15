"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui";

export function LandingNav() {
  const { me } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={
        "fixed inset-x-0 top-0 z-50 transition-all duration-300 " +
        (scrolled
          ? "border-b border-border bg-surface/70 backdrop-blur-xl"
          : "border-b border-transparent bg-transparent")
      }
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" aria-label="Home">
          <Logo />
        </Link>
        <div className="hidden items-center gap-8 text-sm text-fg/70 md:flex">
          <a href="#features" className="transition-colors hover:text-fg">
            Features
          </a>
          <a href="#platform" className="transition-colors hover:text-fg">
            Platform
          </a>
          <a href="#pricing" className="transition-colors hover:text-fg">
            Pricing
          </a>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {me ? (
            <Link href="/dashboard">
              <Button className="rounded-full">Dashboard</Button>
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden text-sm font-medium text-fg/80 transition-colors hover:text-fg sm:inline"
              >
                Sign in
              </Link>
              <Link href="/signup">
                <Button className="rounded-full">Get started</Button>
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
