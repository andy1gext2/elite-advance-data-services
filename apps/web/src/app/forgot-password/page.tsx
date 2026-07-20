"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Alert, Button, Field, Input, PasswordInput } from "@/components/ui";
import { AuthLayout } from "@/components/AuthLayout";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<"request" | "reset">("request");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.forgotPassword(email);
      // In dev (mock email), the backend hands back the code so you can test
      // without an inbox; prefill it.
      if (res.dev_code) setCode(res.dev_code);
      setNotice(
        "If that email is registered, we sent a 6-digit reset code. Enter it below."
      );
      setStep("reset");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.resetPassword(email, code.trim(), newPassword);
      router.replace("/login?reset=1");
      return;
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not reset password"
      );
    } finally {
      setBusy(false);
    }
  }

  if (step === "request") {
    return (
      <AuthLayout
        title="Reset your password"
        subtitle="Enter your email and we'll send you a reset code."
      >
        <form onSubmit={requestCode} className="space-y-4">
          <Field label="Email">
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </Field>
          <Alert>{error}</Alert>
          <Button type="submit" loading={busy} className="w-full">
            Send reset code
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          Remembered it?{" "}
          <Link href="/login" className="text-brand hover:underline">
            Back to sign in
          </Link>
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Enter your code"
      subtitle="Check your inbox for the 6-digit code, then choose a new password."
    >
      <form onSubmit={resetPassword} className="space-y-4">
        {notice && (
          <p className="rounded-lg border border-border bg-bg px-3 py-2 text-sm text-muted">
            {notice}
          </p>
        )}
        <Field label="Reset code">
          <Input
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="123456"
            maxLength={6}
            required
          />
        </Field>
        <Field label="New password" hint="At least 8 characters.">
          <PasswordInput
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={8}
            required
          />
        </Field>
        <Alert>{error}</Alert>
        <Button type="submit" loading={busy} className="w-full">
          Set new password
        </Button>
        <button
          type="button"
          onClick={() => {
            setStep("request");
            setError("");
            setNotice("");
          }}
          className="w-full text-center text-sm text-muted hover:text-fg"
        >
          Use a different email
        </button>
      </form>
    </AuthLayout>
  );
}
