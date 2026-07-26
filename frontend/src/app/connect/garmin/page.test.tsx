import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConnectGarminPage from "@/app/connect/garmin/page";

describe("ConnectGarminPage", () => {
  it("renders the email/password form with no message by default", async () => {
    const ui = await ConnectGarminPage({ searchParams: Promise.resolve({}) });
    render(ui);

    expect(screen.getByPlaceholderText(/garmin email/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/garmin password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /connect/i })).toBeInTheDocument();
    expect(screen.queryByText(/connected/i)).not.toBeInTheDocument();
  });

  it("renders the mfa code form, not the password form, when a pending login is present", async () => {
    const ui = await ConnectGarminPage({
      searchParams: Promise.resolve({ pending_login_id: "pending-123" }),
    });
    render(ui);

    expect(screen.getByPlaceholderText(/mfa code/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/garmin password/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit code/i })).toBeInTheDocument();
  });

  it("renders the mapped message when redirected back with an invalid-credentials error", async () => {
    const ui = await ConnectGarminPage({
      searchParams: Promise.resolve({ error: "invalid_credentials" }),
    });
    render(ui);

    expect(screen.getByText(/doesn't work/i)).toBeInTheDocument();
  });

  it("renders a success message after connecting", async () => {
    const ui = await ConnectGarminPage({ searchParams: Promise.resolve({ success: "1" }) });
    render(ui);

    expect(screen.getByText(/garmin account connected/i)).toBeInTheDocument();
  });
});
