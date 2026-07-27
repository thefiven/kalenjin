import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCookieStore = {
  get: vi.fn(),
};
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(mockCookieStore) }));

const { default: LoginPage } = await import("@/app/login/page");

describe("LoginPage", () => {
  beforeEach(() => {
    mockCookieStore.get.mockReset();
  });

  it("renders a sign-in link and no error message in French by default", async () => {
    mockCookieStore.get.mockReturnValue(undefined);

    const ui = await LoginPage({ searchParams: Promise.resolve({}) });
    render(ui);

    expect(screen.getByRole("button", { name: "Se connecter avec Google" })).toHaveAttribute(
      "href",
      expect.stringContaining("/auth/google/login"),
    );
    expect(screen.queryByText(/invité/i)).not.toBeInTheDocument();
  });

  it("renders the not-invited message in French when redirected back with that error", async () => {
    mockCookieStore.get.mockReturnValue(undefined);

    const ui = await LoginPage({ searchParams: Promise.resolve({ error: "not_invited" }) });
    render(ui);

    expect(screen.getByText(/n'a pas encore été invité/i)).toBeInTheDocument();
  });

  it("renders the page in English when the NEXT_LOCALE cookie is en", async () => {
    mockCookieStore.get.mockReturnValue({ value: "en" });

    const ui = await LoginPage({ searchParams: Promise.resolve({ error: "not_invited" }) });
    render(ui);

    expect(screen.getByRole("button", { name: "Sign in with Google" })).toBeInTheDocument();
    expect(screen.getByText(/hasn't been invited/i)).toBeInTheDocument();
  });
});
