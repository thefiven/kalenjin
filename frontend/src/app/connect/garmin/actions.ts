"use server";

import { redirect } from "next/navigation";
import { connectGarminAccount, disconnectGarminAccount, submitGarminMfaCode } from "@/lib/api";

export async function connectGarminAction(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "").trim();
  if (!email || !password) {
    redirect("/connect/garmin?error=missing_fields");
  }

  const result = await connectGarminAccount(email, password);
  if (!result.success) {
    // A fixed code, not `result.error` verbatim — mirrors connect-gemini-error.ts's pattern.
    redirect("/connect/garmin?error=invalid_credentials");
  }
  if (result.status === "mfa_required") {
    redirect(`/connect/garmin?pending_login_id=${encodeURIComponent(result.pendingLoginId)}`);
  }
  redirect("/connect/garmin?success=1");
}

export async function submitGarminMfaAction(formData: FormData): Promise<void> {
  const pendingLoginId = String(formData.get("pending_login_id") ?? "").trim();
  const mfaCode = String(formData.get("mfa_code") ?? "").trim();
  if (!pendingLoginId || !mfaCode) {
    redirect("/connect/garmin?error=missing_mfa_code");
  }

  const result = await submitGarminMfaCode(pendingLoginId, mfaCode);
  if (!result.success) {
    // The pending login is consumed server-side even on a rejected code (issue #30) —
    // send the user back to the start rather than retrying a now-dead pending_login_id.
    redirect("/connect/garmin?error=invalid_mfa_code");
  }
  redirect("/connect/garmin?success=1");
}

export async function disconnectGarminAction(): Promise<void> {
  const result = await disconnectGarminAccount();
  if (!result.success) {
    redirect("/connect/garmin?error=disconnect_failed");
  }
  redirect("/connect/garmin?disconnected=1");
}
