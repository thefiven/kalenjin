import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RapportPanel } from "@/components/rapport-panel";
import { rapport } from "@/test-support/fixtures";

describe("RapportPanel", () => {
  it("renders the strengths and improvements", () => {
    render(
      <RapportPanel
        rapport={rapport({ strengths: "Good pace.", improvements: "Add strides." })}
      />,
    );

    expect(screen.getByText("Good pace.")).toBeInTheDocument();
    expect(screen.getByText("Add strides.")).toBeInTheDocument();
  });

  it("shows a placeholder when no rapport has been generated yet", () => {
    render(<RapportPanel rapport={null} />);

    expect(screen.getByText(/no rapport/i)).toBeInTheDocument();
  });
});
