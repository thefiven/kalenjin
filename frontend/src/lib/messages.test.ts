import { describe, expect, it } from "vitest";
import { LOCALES } from "@/lib/locale";
import { MESSAGES } from "@/lib/i18n";

function flattenKeys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([key, nested]) =>
    flattenKeys(nested, prefix ? `${prefix}.${key}` : key),
  );
}

describe("message files", () => {
  it("declare the same keys across every supported locale", () => {
    const [reference, ...rest] = LOCALES.map((locale) => flattenKeys(MESSAGES[locale]).sort());

    for (const keys of rest) {
      expect(keys).toEqual(reference);
    }
  });
});
