import { Button } from "@/components/ui/button";
import { getPageTranslator } from "@/lib/i18n";
import { loginErrorKey } from "@/lib/login-error";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const errorKey = loginErrorKey(error);
  const t = await getPageTranslator("login");

  // Literal keys (rather than a dynamic `errors.${errorKey}` template) so a
  // renamed or missing message key surfaces as a build-time/dev warning
  // instead of only at runtime on a page a user hits mid-failed-login.
  let message: string | null = null;
  switch (errorKey) {
    case "invalidState":
      message = t("errors.invalidState");
      break;
    case "notInvited":
      message = t("errors.notInvited");
      break;
    case "googleAuthFailed":
      message = t("errors.googleAuthFailed");
      break;
    case "default":
      message = t("errors.default");
      break;
  }

  return (
    <main className="flex-1 flex flex-col items-center justify-center gap-4">
      <h1 className="text-lg font-medium">{t("title")}</h1>
      {message && <p className="text-sm text-destructive">{message}</p>}
      <Button
        nativeButton={false}
        render={<a href={`${API_URL}/auth/google/login`}>{t("signInWithGoogle")}</a>}
      />
    </main>
  );
}
