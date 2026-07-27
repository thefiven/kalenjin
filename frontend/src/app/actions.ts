"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE_NAME } from "@/lib/auth";
import { LOCALE_COOKIE_NAME, type Locale } from "@/lib/locale";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const ONE_YEAR_IN_SECONDS = 60 * 60 * 24 * 365;

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME);
  if (session) {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: { Cookie: `${SESSION_COOKIE_NAME}=${session.value}` },
    });
  }
  // Cleared here regardless of the backend call's outcome: the cookie is the only
  // thing actually gating access (proxy.ts, get_current_user), the backend has no
  // server-side session to invalidate for a stateless signed token.
  cookieStore.delete(SESSION_COOKIE_NAME);
  redirect("/login");
}

export async function setLocaleAction(locale: Locale): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(LOCALE_COOKIE_NAME, locale, { maxAge: ONE_YEAR_IN_SECONDS, path: "/" });
}
