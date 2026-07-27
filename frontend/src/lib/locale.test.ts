import { describe, expect, it } from "vitest";
import { resolveLocale } from "@/lib/locale";

describe("resolveLocale", () => {
  it("defaults to fr when there is no cookie", () => {
    expect(resolveLocale(undefined)).toBe("fr");
  });

  it("returns en for an explicit en cookie", () => {
    expect(resolveLocale("en")).toBe("en");
  });

  it("returns fr for an explicit fr cookie", () => {
    expect(resolveLocale("fr")).toBe("fr");
  });

  it("falls back to fr for an invalid cookie value", () => {
    expect(resolveLocale("de")).toBe("fr");
  });
});
