import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";

const refreshMock = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: refreshMock }) }));

const setLocaleActionMock = vi.fn().mockResolvedValue(undefined);
vi.mock("@/app/actions", () => ({
  setLocaleAction: (locale: string) => setLocaleActionMock(locale),
}));

const { LocaleToggle } = await import("@/components/locale-toggle");

describe("LocaleToggle", () => {
  beforeEach(() => {
    refreshMock.mockReset();
    setLocaleActionMock.mockReset().mockResolvedValue(undefined);
  });

  it("switches to English and refreshes the route when clicked while in French", async () => {
    render(
      <NextIntlClientProvider locale="fr" messages={fr}>
        <LocaleToggle />
      </NextIntlClientProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Changer de langue" }));

    await waitFor(() => {
      expect(setLocaleActionMock).toHaveBeenCalledWith("en");
      expect(refreshMock).toHaveBeenCalled();
    });
  });

  it("switches to French when clicked while in English", async () => {
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <LocaleToggle />
      </NextIntlClientProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Toggle language" }));

    await waitFor(() => {
      expect(setLocaleActionMock).toHaveBeenCalledWith("fr");
    });
  });
});
