import { cookies } from "next/headers";
import { createTranslator, type NamespaceKeys, type NestedKeyOf } from "next-intl";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { LOCALE_COOKIE_NAME, resolveLocale, type Locale } from "@/lib/locale";

export const MESSAGES: Record<Locale, typeof fr> = { fr, en };

export async function loadLocaleMessages() {
  const cookieStore = await cookies();
  const locale = resolveLocale(cookieStore.get(LOCALE_COOKIE_NAME)?.value);
  return { locale, messages: MESSAGES[locale] };
}

// A synchronous, environment-agnostic alternative to next-intl/server's
// getTranslations: that module resolves to a client-only stub outside of
// Next's own "react-server" build condition (e.g. under Vitest), which
// breaks unit-testing Server Components that call it directly.
export async function getPageTranslator<
  Namespace extends NamespaceKeys<typeof fr, NestedKeyOf<typeof fr>>,
>(namespace: Namespace) {
  const { locale, messages } = await loadLocaleMessages();
  return createTranslator({ locale, messages, namespace });
}
