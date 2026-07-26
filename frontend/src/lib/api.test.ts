import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCookieStore = { get: vi.fn() };
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(mockCookieStore) }));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const { fetchActivities } = await import("@/lib/api");

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
