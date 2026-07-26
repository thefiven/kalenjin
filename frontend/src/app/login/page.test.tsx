import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoginPage from "@/app/login/page";

describe("LoginPage", () => {
  it("renders a sign-in link and no error message by default", async () => {
    const ui = await LoginPage({ searchParams: Promise.resolve({}) });
    render(ui);

    expect(screen.getByRole("button", { name: /sign in with google/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/auth/google/login"),
    );
    expect(screen.queryByText(/hasn't been invited/i)).not.toBeInTheDocument();
  });

  it("renders the not-invited message when redirected back with that error", async () => {
    const ui = await LoginPage({ searchParams: Promise.resolve({ error: "not_invited" }) });
    render(ui);

    expect(screen.getByText(/hasn't been invited/i)).toBeInTheDocument();
  });
});
