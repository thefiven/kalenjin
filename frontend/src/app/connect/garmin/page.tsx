import { Button } from "@/components/ui/button";
import { connectGarminErrorMessage } from "@/lib/connect-garmin-error";
import { connectGarminAction, submitGarminMfaAction } from "./actions";

export default async function ConnectGarminPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; success?: string; pending_login_id?: string }>;
}) {
  const { error, success, pending_login_id: pendingLoginId } = await searchParams;
  const message = connectGarminErrorMessage(error);

  return (
    <main className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-lg font-medium">Connect your Garmin account</h1>
      <p className="max-w-sm text-center text-sm text-muted-foreground">
        Kalenjin uses your own Garmin login to pull activities and push planned workouts
        (ADR-0006) — it&apos;s encrypted at rest and never shared with other users.
      </p>
      {message && <p className="text-sm text-destructive">{message}</p>}
      {success && <p className="text-sm text-emerald-600">Garmin account connected.</p>}
      {pendingLoginId ? (
        <form action={submitGarminMfaAction} className="flex w-full max-w-sm flex-col gap-2">
          <input type="hidden" name="pending_login_id" value={pendingLoginId} />
          <input
            type="text"
            name="mfa_code"
            placeholder="MFA code"
            required
            className="rounded border bg-background px-2 py-1 text-sm"
          />
          <Button type="submit">Submit code</Button>
        </form>
      ) : (
        <form action={connectGarminAction} className="flex w-full max-w-sm flex-col gap-2">
          <input
            type="email"
            name="email"
            placeholder="Garmin email"
            required
            className="rounded border bg-background px-2 py-1 text-sm"
          />
          <input
            type="password"
            name="password"
            placeholder="Garmin password"
            required
            className="rounded border bg-background px-2 py-1 text-sm"
          />
          <Button type="submit">Connect</Button>
        </form>
      )}
    </main>
  );
}
