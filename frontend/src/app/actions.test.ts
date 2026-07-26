import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCookieStore = {
  get: vi.fn(),
  delete: vi.fn(),
};
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(mockCookieStore) }));

const redirectMock = vi.fn();
vi.mock("next/navigation", () => ({ redirect: (path: string) => redirectMock(path) }));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const { logoutAction } = await import("@/app/actions");

describe("logoutAction", () => {
  beforeEach(() => {
    mockCookieStore.get.mockReset();
    mockCookieStore.delete.mockReset();
    redirectMock.mockReset();
    fetchMock.mockReset().mockResolvedValue({ ok: true });
  });

  it("calls the backend logout endpoint when a session cookie exists", async () => {
    mockCookieStore.get.mockReturnValue({ value: "some-token" });

    await logoutAction();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/logout"),
      expect.objectContaining({
        method: "POST",
        headers: { Cookie: "kalenjin_session=some-token" },
      }),
    );
  });

  it("skips the backend call when there is no session cookie", async () => {
    mockCookieStore.get.mockReturnValue(undefined);

    await logoutAction();

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("clears the cookie and redirects to /login regardless", async () => {
    mockCookieStore.get.mockReturnValue({ value: "some-token" });

    await logoutAction();

    expect(mockCookieStore.delete).toHaveBeenCalledWith("kalenjin_session");
    expect(redirectMock).toHaveBeenCalledWith("/login");
  });
});
