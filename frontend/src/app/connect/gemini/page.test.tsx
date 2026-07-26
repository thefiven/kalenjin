import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConnectGeminiPage from "@/app/connect/gemini/page";

describe("ConnectGeminiPage", () => {
  it("renders the form with no message by default", async () => {
    const ui = await ConnectGeminiPage({ searchParams: Promise.resolve({}) });
    render(ui);

    expect(screen.getByPlaceholderText(/gemini api key/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(screen.queryByText(/connected/i)).not.toBeInTheDocument();
  });

  it("renders the mapped message when redirected back with an invalid-key error", async () => {
    const ui = await ConnectGeminiPage({ searchParams: Promise.resolve({ error: "invalid_key" }) });
    render(ui);

    expect(screen.getByText(/doesn't work/i)).toBeInTheDocument();
  });

  it("renders a success message after connecting", async () => {
    const ui = await ConnectGeminiPage({ searchParams: Promise.resolve({ success: "1" }) });
    render(ui);

    expect(screen.getByText(/gemini key connected/i)).toBeInTheDocument();
  });
});
