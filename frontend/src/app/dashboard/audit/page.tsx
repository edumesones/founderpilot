/**
 * Audit dashboard page.
 */

"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { AuditDashboard } from "@/components/audit";

function AuditPageContent() {
  return <AuditDashboard />;
}

export default function AuditPage() {
  return (
    <AuthGuard>
      <AuditPageContent />
    </AuthGuard>
  );
}
