import { describe, expect, it } from "vitest";
import { connectGeminiErrorMessage } from "@/lib/connect-gemini-error";

describe("connectGeminiErrorMessage", () => {
  it("returns null when there is no error", () => {
    expect(connectGeminiErrorMessage(undefined)).toBeNull();
  });

  it("returns a specific message for a missing key", () => {
    expect(connectGeminiErrorMessage("missing_key")).toMatch(/enter your gemini api key/i);
  });

  it("returns a specific message for an invalid key", () => {
    expect(connectGeminiErrorMessage("invalid_key")).toMatch(/doesn't work/i);
  });

  it("falls back to a generic message for an unrecognized code, never echoing raw input", () => {
    expect(connectGeminiErrorMessage("<script>alert(1)</script>")).toBe(
      "Something went wrong — try again.",
    );
  });
});
