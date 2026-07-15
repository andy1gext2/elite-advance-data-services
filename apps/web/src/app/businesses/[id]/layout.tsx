"use client";

import { use } from "react";
import { WorkspaceShell } from "@/components/WorkspaceShell";

// Wraps every page under a business in the command-center shell (sidebar + top
// bar + auth). Pages render only their own content.
export default function BusinessLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WorkspaceShell businessId={id}>{children}</WorkspaceShell>;
}
