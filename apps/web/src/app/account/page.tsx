"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/AppShell";
import { Alert, Button, Card, Field, Input, PageHeader } from "@/components/ui";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-1 text-sm font-semibold">{children}</h3>;
}

export default function AccountPage() {
  return (
    <AppShell>
      <AccountSettings />
    </AppShell>
  );
}

function AccountSettings() {
  const { me, logout, refreshMe } = useAuth();

  // Profile
  const [fullName, setFullName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  // Password
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [pwMsg, setPwMsg] = useState("");

  // Export
  const [exporting, setExporting] = useState(false);

  // Delete
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deletePw, setDeletePw] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [error, setError] = useState("");

  useEffect(() => {
    setFullName(me?.user.full_name ?? "");
  }, [me]);

  async function saveProfile() {
    setError("");
    setProfileMsg("");
    setSavingProfile(true);
    try {
      await api.updateProfile(fullName.trim() || null);
      await refreshMe();
      setProfileMsg("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save profile");
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword() {
    setError("");
    setPwMsg("");
    if (newPw.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    setSavingPw(true);
    try {
      await api.changePassword(currentPw, newPw);
      setCurrentPw("");
      setNewPw("");
      setPwMsg("Password updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change password");
    } finally {
      setSavingPw(false);
    }
  }

  async function exportData() {
    setError("");
    setExporting(true);
    try {
      const data = await api.exportAccount();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `elite-advance-data-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not export your data");
    } finally {
      setExporting(false);
    }
  }

  async function deleteAccount() {
    setError("");
    setDeleting(true);
    try {
      await api.deleteAccount(deletePw);
      logout(); // clears the (now-dead) session and redirects to /login
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete your account");
      setDeleting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Account settings"
        subtitle="Manage your profile, password, and data."
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      {/* Profile */}
      <Card className="mt-4">
        <SectionTitle>Profile</SectionTitle>
        <p className="mb-3 text-xs text-muted">
          Signed in as <span className="text-fg">{me?.user.email}</span>
        </p>
        <div className="max-w-md space-y-3">
          <Field label="Full name">
            <Input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
            />
          </Field>
          <div className="flex items-center gap-3">
            <Button onClick={saveProfile} loading={savingProfile}>
              Save profile
            </Button>
            {profileMsg && <span className="text-sm text-green-600 dark:text-green-500">{profileMsg}</span>}
          </div>
        </div>
      </Card>

      {/* Password */}
      <Card className="mt-4">
        <SectionTitle>Change password</SectionTitle>
        <div className="max-w-md space-y-3">
          <Field label="Current password">
            <Input
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              autoComplete="current-password"
            />
          </Field>
          <Field label="New password">
            <Input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              autoComplete="new-password"
              placeholder="At least 8 characters"
            />
          </Field>
          <div className="flex items-center gap-3">
            <Button
              onClick={savePassword}
              loading={savingPw}
              disabled={!currentPw || !newPw}
            >
              Update password
            </Button>
            {pwMsg && <span className="text-sm text-green-600 dark:text-green-500">{pwMsg}</span>}
          </div>
        </div>
      </Card>

      {/* Data export */}
      <Card className="mt-4">
        <SectionTitle>Your data</SectionTitle>
        <p className="mb-3 text-sm text-muted">
          Download a portable copy of everything in your account — your profile and
          every business you belong to, including content, campaigns, schedules,
          reviews, and products. Connected-account tokens are never included.
        </p>
        <Button variant="secondary" onClick={exportData} loading={exporting}>
          ⬇ Export my data (JSON)
        </Button>
      </Card>

      {/* Danger zone */}
      <Card className="mt-4 border-red-500/40">
        <SectionTitle>
          <span className="text-red-500">Danger zone</span>
        </SectionTitle>
        <p className="mb-3 text-sm text-muted">
          Permanently delete your account and every business you own — all content,
          schedules, reviews, products, and connected-account tokens. This cannot be
          undone.
        </p>
        {!confirmOpen ? (
          <Button
            variant="secondary"
            className="border-red-500/50 text-red-500 hover:bg-red-500/10"
            onClick={() => setConfirmOpen(true)}
          >
            Delete my account
          </Button>
        ) : (
          <div className="max-w-md space-y-3 rounded-lg border border-red-500/40 bg-red-500/5 p-4">
            <p className="text-sm font-medium text-red-500">
              This is permanent. Enter your password to confirm.
            </p>
            <Input
              type="password"
              value={deletePw}
              onChange={(e) => setDeletePw(e.target.value)}
              autoComplete="current-password"
              placeholder="Your password"
            />
            <div className="flex items-center gap-2">
              <Button
                className="bg-red-600 text-white hover:bg-red-700"
                onClick={deleteAccount}
                loading={deleting}
                disabled={!deletePw}
              >
                Permanently delete
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setConfirmOpen(false);
                  setDeletePw("");
                }}
                disabled={deleting}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Card>
    </>
  );
}
