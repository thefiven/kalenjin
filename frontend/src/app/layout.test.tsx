import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCookieStore = {
  get: vi.fn(),
};
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(mockCookieStore) }));
vi.mock("next/font/google", () => ({
  Geist: () => ({ variable: "--font-geist-sans" }),
  Geist_Mono: () => ({ variable: "--font-geist-mono" }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

const { default: RootLayout } = await import("@/app/layout");

describe("RootLayout", () => {
  beforeEach(() => {
    mockCookieStore.get.mockReset();
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    });
  });

  it("renders the nav in French by default", async () => {
    mockCookieStore.get.mockReturnValue(undefined);

    const ui = await RootLayout({ children: <div /> });
    render(ui);

    expect(screen.getByRole("link", { name: "Tableau de bord" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Se déconnecter" })).toBeInTheDocument();
    // <html> can't be validly rendered as a div's child via testing-library,
    // so its `lang` prop is asserted on the returned element directly.
    expect(ui.props.lang).toBe("fr");
  });

  it("renders the nav in English when the NEXT_LOCALE cookie is en", async () => {
    mockCookieStore.get.mockReturnValue({ value: "en" });

    const ui = await RootLayout({ children: <div /> });
    render(ui);

    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(ui.props.lang).toBe("en");
  });
});
