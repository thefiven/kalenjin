"use server";

import { redirect } from "next/navigation";
import { setGeminiApiKey } from "@/lib/api";

export async function connectGeminiAction(formData: FormData): Promise<void> {
  const apiKey = String(formData.get("api_key") ?? "").trim();
  if (!apiKey) {
    redirect("/connect/gemini?error=missing_key");
  }

  const result = await setGeminiApiKey(apiKey);
  if (!result.success) {
    // A fixed code, not `result.error` verbatim: the backend's raw detail text must
    // not flow through the URL/DOM unfiltered (mirrors login-error.ts's pattern).
    redirect("/connect/gemini?error=invalid_key");
  }

  redirect("/connect/gemini?success=1");
}
