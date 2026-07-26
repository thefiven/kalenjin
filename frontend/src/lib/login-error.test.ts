import { describe, expect, it } from "vitest";
import { loginErrorMessage } from "@/lib/login-error";

describe("loginErrorMessage", () => {
  it("returns null when there is no error", () => {
    expect(loginErrorMessage(undefined)).toBeNull();
  });

  it("returns a specific message for the not-invited error", () => {
    expect(loginErrorMessage("not_invited")).toMatch(/hasn't been invited/);
  });

  it("returns a specific message for an invalid OAuth state", () => {
    expect(loginErrorMessage("invalid_state")).toMatch(/try again/);
  });

  it("falls back to a generic message for an unrecognized error code", () => {
    expect(loginErrorMessage("something_unexpected")).toMatch(/went wrong signing in/);
  });
});
