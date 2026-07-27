export type Locale = "fr" | "en";

export const LOCALE_COOKIE_NAME = "NEXT_LOCALE";

export function resolveLocale(cookieValue: string | undefined): Locale {
  return cookieValue === "en" ? "en" : "fr";
}
