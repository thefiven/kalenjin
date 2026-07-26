import { describe, expect, it } from "vitest";
import { connectGarminErrorMessage } from "@/lib/connect-garmin-error";

describe("connectGarminErrorMessage", () => {
  it("returns null when there is no error", () => {
    expect(connectGarminErrorMessage(undefined)).toBeNull();
  });

  it("returns a specific message for missing fields", () => {
    expect(connectGarminErrorMessage("missing_fields")).toMatch(/enter your garmin/i);
  });

  it("returns a specific message for invalid credentials", () => {
    expect(connectGarminErrorMessage("invalid_credentials")).toMatch(/doesn't work/i);
  });

  it("returns a specific message for a missing mfa code", () => {
    expect(connectGarminErrorMessage("missing_mfa_code")).toMatch(/mfa code/i);
  });

  it("returns a specific message for an invalid mfa code", () => {
    expect(connectGarminErrorMessage("invalid_mfa_code")).toMatch(/didn't work/i);
  });

  it("falls back to a generic message for an unrecognized code, never echoing raw input", () => {
    expect(connectGarminErrorMessage("<script>alert(1)</script>")).toBe(
      "Something went wrong — try again.",
    );
  });
});
