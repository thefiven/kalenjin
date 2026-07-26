import { beforeEach, describe, expect, it, vi } from "vitest";

const setGeminiApiKeyMock = vi.fn();
vi.mock("@/lib/api", () => ({ setGeminiApiKey: (key: string) => setGeminiApiKeyMock(key) }));

const redirectMock = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    redirectMock(path);
    throw new Error(`NEXT_REDIRECT:${path}`);
  },
}));

const { connectGeminiAction } = await import("@/app/connect/gemini/actions");

function formDataWith(apiKey: string | null): FormData {
  const formData = new FormData();
  if (apiKey !== null) formData.set("api_key", apiKey);
  return formData;
}

describe("connectGeminiAction", () => {
  beforeEach(() => {
    setGeminiApiKeyMock.mockReset();
    redirectMock.mockReset();
  });

  it("redirects with an error when the field is left empty", async () => {
    await expect(connectGeminiAction(formDataWith(null))).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/gemini?error=missing_key");
    expect(setGeminiApiKeyMock).not.toHaveBeenCalled();
  });

  it("redirects with a fixed error code when the key is rejected, not the raw backend detail", async () => {
    setGeminiApiKeyMock.mockResolvedValue({ success: false, error: "Invalid Gemini API key" });

    await expect(connectGeminiAction(formDataWith("bad-key"))).rejects.toThrow();

    expect(setGeminiApiKeyMock).toHaveBeenCalledWith("bad-key");
    expect(redirectMock).toHaveBeenCalledWith("/connect/gemini?error=invalid_key");
  });

  it("redirects to a success state when the key is accepted", async () => {
    setGeminiApiKeyMock.mockResolvedValue({ success: true });

    await expect(connectGeminiAction(formDataWith("a-real-key"))).rejects.toThrow();

    expect(redirectMock).toHaveBeenCalledWith("/connect/gemini?success=1");
  });
});
