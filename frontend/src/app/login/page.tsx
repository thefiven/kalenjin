import { Button } from "@/components/ui/button";
import { loginErrorMessage } from "@/lib/login-error";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const message = loginErrorMessage(error);

  return (
    <main className="flex-1 flex flex-col items-center justify-center gap-4">
      <h1 className="text-lg font-medium">Kalenjin</h1>
      {message && <p className="text-sm text-destructive">{message}</p>}
      <Button
        nativeButton={false}
        render={<a href={`${API_URL}/auth/google/login`}>Sign in with Google</a>}
      />
    </main>
  );
}
