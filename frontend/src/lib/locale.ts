export const LOCALES = ["fr", "en"] as const;

export type Locale = (typeof LOCALES)[number];

export const LOCALE_COOKIE_NAME = "NEXT_LOCALE";

export function resolveLocale(cookieValue: string | undefined): Locale {
  return (LOCALES as readonly string[]).includes(cookieValue ?? "")
    ? (cookieValue as Locale)
    : "fr";
}
