import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCookieStore = { get: vi.fn() };
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(mockCookieStore) }));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const { fetchActivities, setGeminiApiKey, disconnectGarminAccount } = await import("@/lib/api");

describe("fetchActivities", () => {
  beforeEach(() => {
    mockCookieStore.get.mockReset();
    fetchMock.mockReset().mockResolvedValue({ ok: true, json: async () => [] });
  });

  it("forwards the session cookie to the backend when present", async () => {
    mockCookieStore.get.mockReturnValue({ value: "abc" });

    await fetchActivities();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).toEqual({ Cookie: "kalenjin_session=abc" });
  });

  it("sends no Cookie header when there is no session", async () => {
    mockCookieStore.get.mockReturnValue(undefined);

    await fetchActivities();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).toEqual({});
  });
});

describe("setGeminiApiKey", () => {
  beforeEach(() => {
    mockCookieStore.get.mockReset();
    fetchMock.mockReset();
  });

  it("returns success when the backend accepts the key", async () => {
    fetchMock.mockResolvedValue({ ok: true });

    const result = await setGeminiApiKey("a-key");

    expect(result).toEqual({ success: true });
  });

  it("surfaces the backend's error detail when the key is rejected", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Invalid Gemini API key" }),
    });

    const result = await setGeminiApiKey("a-bad-key");

    expect(result).toEqual({ success: false, error: "Invalid Gemini API key" });
  });

  it("falls back to a status-based message when the response has no detail", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    });

    const result = await setGeminiApiKey("a-key");

    expect(result).toEqual({ success: false, error: "Failed to save API key: 500" });
  });
});

describe("disconnectGarminAccount", () => {
  beforeEach(() => {
    mockCookieStore.get.mockReset();
    fetchMock.mockReset();
  });

  it("sends a DELETE request and returns success on a 204", async () => {
    fetchMock.mockResolvedValue({ ok: true });

    const result = await disconnectGarminAccount();

    expect(result).toEqual({ success: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/users/me/garmin-credentials");
    expect(init.method).toBe("DELETE");
  });

  it("surfaces the backend's error detail when disconnecting fails", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Not connected" }),
    });

    const result = await disconnectGarminAccount();

    expect(result).toEqual({ success: false, error: "Not connected" });
  });
});
