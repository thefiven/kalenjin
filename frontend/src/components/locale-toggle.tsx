"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { setLocaleAction } from "@/app/actions";
import { resolveLocale, type Locale } from "@/lib/locale";
import { Button } from "@/components/ui/button";

export function LocaleToggle() {
  const locale = resolveLocale(useLocale());
  const t = useTranslations("nav");
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
      aria-label={t("toggleLocale")}
      onClick={toggleLocale}
      disabled={isPending}
    >
      {locale === "fr" ? "EN" : "FR"}
    </Button>
  );
}
