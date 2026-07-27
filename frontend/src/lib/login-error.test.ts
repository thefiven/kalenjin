import { describe, expect, it } from "vitest";
import { loginErrorKey } from "@/lib/login-error";

describe("loginErrorKey", () => {
  it("returns null when there is no error", () => {
    expect(loginErrorKey(undefined)).toBeNull();
  });

  it("returns the notInvited key for the not-invited error", () => {
    expect(loginErrorKey("not_invited")).toBe("notInvited");
  });

  it("returns the invalidState key for an invalid OAuth state", () => {
    expect(loginErrorKey("invalid_state")).toBe("invalidState");
  });

  it("returns the googleAuthFailed key when Google couldn't confirm identity", () => {
    expect(loginErrorKey("google_auth_failed")).toBe("googleAuthFailed");
  });

  it("falls back to the default key for an unrecognized error code", () => {
    expect(loginErrorKey("something_unexpected")).toBe("default");
  });
});
