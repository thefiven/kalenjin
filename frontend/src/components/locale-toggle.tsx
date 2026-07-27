"use client";

import { useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { setLocaleAction } from "@/app/actions";
import type { Locale } from "@/lib/locale";
import { Button } from "@/components/ui/button";

export function LocaleToggle() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function toggleLocale() {
    const nextLocale: Locale = locale === "fr" ? "en" : "fr";
    startTransition(async () => {
      await setLocaleAction(nextLocale);
      router.refresh();
    });
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      aria-label="Toggle language"
      onClick={toggleLocale}
      disabled={isPending}
    >
      {locale === "fr" ? "EN" : "FR"}
    </Button>
  );
}
