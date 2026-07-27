import { beforeEach, describe, expect, it, vi } from "vitest";

const connectGarminAccountMock = vi.fn();
const submitGarminMfaCodeMock = vi.fn();
const disconnectGarminAccountMock = vi.fn();
vi.mock("@/lib/api", () => ({
  connectGarminAccount: (email: string, password: string) =>
    connectGarminAccountMock(email, password),
  submitGarminMfaCode: (pendingLoginId: string, mfaCode: string) =>
    submitGarminMfaCodeMock(pendingLoginId, mfaCode),
  disconnectGarminAccount: () => disconnectGarminAccountMock(),
}));

const redirectMock = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    redirectMock(path);
    throw new Error(`NEXT_REDIRECT:${path}`);
  },
}));

const { connectGarminAction, submitGarminMfaAction, disconnectGarminAction } = await import(
  "@/app/connect/garmin/actions"
);

function formDataWith(fields: Record<string, string | null>): FormData {
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    if (value !== null) formData.set(key, value);
  }
  return formData;
}

describe("connectGarminAction", () => {
  beforeEach(() => {
    connectGarminAccountMock.mockReset();
    redirectMock.mockReset();
  });

  it("redirects with an error when either field is left empty", async () => {
    await expect(
      connectGarminAction(formDataWith({ email: null, password: "hunter2" })),
    ).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?error=missing_fields");
    expect(connectGarminAccountMock).not.toHaveBeenCalled();
  });

  it("redirects with a fixed error code when credentials are rejected", async () => {
    connectGarminAccountMock.mockResolvedValue({ success: false, error: "Invalid credentials" });

    await expect(
      connectGarminAction(formDataWith({ email: "a@b.com", password: "wrong" })),
    ).rejects.toThrow();

    expect(connectGarminAccountMock).toHaveBeenCalledWith("a@b.com", "wrong");
    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?error=invalid_credentials");
  });

  it("redirects to the mfa step, carrying the pending login id, when mfa is required", async () => {
    connectGarminAccountMock.mockResolvedValue({
      success: true,
      status: "mfa_required",
      pendingLoginId: "pending-123",
    });

    await expect(
      connectGarminAction(formDataWith({ email: "a@b.com", password: "hunter2" })),
    ).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?pending_login_id=pending-123");
  });

  it("redirects to a success state when connected without mfa", async () => {
    connectGarminAccountMock.mockResolvedValue({ success: true, status: "connected" });

    await expect(
      connectGarminAction(formDataWith({ email: "a@b.com", password: "hunter2" })),
    ).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?success=1");
  });
});

describe("submitGarminMfaAction", () => {
  beforeEach(() => {
    submitGarminMfaCodeMock.mockReset();
    redirectMock.mockReset();
  });

  it("redirects with an error when the code is left empty", async () => {
    await expect(
      submitGarminMfaAction(formDataWith({ pending_login_id: "pending-123", mfa_code: null })),
    ).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?error=missing_mfa_code");
    expect(submitGarminMfaCodeMock).not.toHaveBeenCalled();
  });

  it("redirects back to the start, not the dead pending login, when the code is rejected", async () => {
    submitGarminMfaCodeMock.mockResolvedValue({ success: false, error: "Invalid code" });

    await expect(
      submitGarminMfaAction(formDataWith({ pending_login_id: "pending-123", mfa_code: "000000" })),
    ).rejects.toThrow();

    expect(submitGarminMfaCodeMock).toHaveBeenCalledWith("pending-123", "000000");
    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?error=invalid_mfa_code");
  });

  it("redirects to a success state when the code is accepted", async () => {
    submitGarminMfaCodeMock.mockResolvedValue({ success: true, status: "connected" });

    await expect(
      submitGarminMfaAction(formDataWith({ pending_login_id: "pending-123", mfa_code: "123456" })),
    ).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?success=1");
  });
});

describe("disconnectGarminAction", () => {
  beforeEach(() => {
    disconnectGarminAccountMock.mockReset();
    redirectMock.mockReset();
  });

  it("redirects to a disconnected state on success", async () => {
    disconnectGarminAccountMock.mockResolvedValue({ success: true });

    await expect(disconnectGarminAction()).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?disconnected=1");
  });

  it("redirects with a fixed error code when disconnecting fails", async () => {
    disconnectGarminAccountMock.mockResolvedValue({ success: false, error: "boom" });

    await expect(disconnectGarminAction()).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/garmin?error=disconnect_failed");
  });
});
