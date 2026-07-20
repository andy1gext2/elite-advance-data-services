"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Alert, Button, Field, Input, PasswordInput } from "@/components/ui";
import { AuthLayout } from "@/components/AuthLayout";

export default function LoginPage() {
  const { me, loading, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && me) router.replace("/dashboard");
  }, [loading, me, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your marketing HQ.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email">
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Password">
          <PasswordInput
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        <Alert>{error}</Alert>
        <Button type="submit" loading={busy} className="w-full">
          Sign in
        </Button>
      </form>
      <p className="mt-4 text-center text-sm text-muted">
        No account?{" "}
        <Link href="/signup" className="text-brand hover:underline">
          Create one
        </Link>
      </p>
    </AuthLayout>
  );
}
