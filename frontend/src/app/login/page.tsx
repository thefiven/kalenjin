import { createTranslator } from "next-intl";
import { Button } from "@/components/ui/button";
import { loadLocaleMessages } from "@/lib/i18n";
import { loginErrorKey } from "@/lib/login-error";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const errorKey = loginErrorKey(error);

  const { locale, messages } = await loadLocaleMessages();
  const t = createTranslator({ locale, messages, namespace: "login" });

  return (
    <main className="flex-1 flex flex-col items-center justify-center gap-4">
      <h1 className="text-lg font-medium">{t("title")}</h1>
      {errorKey && <p className="text-sm text-destructive">{t(`errors.${errorKey}`)}</p>}
      <Button
        nativeButton={false}
        render={<a href={`${API_URL}/auth/google/login`}>{t("signInWithGoogle")}</a>}
      />
    </main>
  );
}
