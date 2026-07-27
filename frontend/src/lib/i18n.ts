import { cookies } from "next/headers";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { LOCALE_COOKIE_NAME, resolveLocale } from "@/lib/locale";

const MESSAGES = { fr, en };

export async function loadLocaleMessages() {
  const cookieStore = await cookies();
  const locale = resolveLocale(cookieStore.get(LOCALE_COOKIE_NAME)?.value);
  return { locale, messages: MESSAGES[locale] };
}
