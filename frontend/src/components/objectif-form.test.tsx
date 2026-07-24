import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ObjectifForm } from "@/components/objectif-form";

vi.mock("@/app/plan/actions", () => ({
  createObjectifAction: vi.fn(),
}));

describe("ObjectifForm", () => {
  it("renders the fields needed to create an objectif", () => {
    render(<ObjectifForm />);

    expect(screen.getByText(/sport/i)).toBeInTheDocument();
    expect(screen.getByText(/target distance/i)).toBeInTheDocument();
    expect(screen.getByText(/target date/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create plan/i })).toBeInTheDocument();
  });
});
