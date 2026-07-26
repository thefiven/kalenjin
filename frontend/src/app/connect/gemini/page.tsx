import { Button } from "@/components/ui/button";
import { connectGeminiErrorMessage } from "@/lib/connect-gemini-error";
import { connectGeminiAction } from "./actions";

export default async function ConnectGeminiPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; success?: string }>;
}) {
  const { error, success } = await searchParams;
  const message = connectGeminiErrorMessage(error);

  return (
    <main className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-lg font-medium">Connect your Gemini API key</h1>
      <p className="max-w-sm text-center text-sm text-muted-foreground">
        Kalenjin uses your own Gemini API key for AI-generated plans and rapports (ADR-0007) —
        it&apos;s encrypted at rest and never shared with other users.
      </p>
      {message && <p className="text-sm text-destructive">{message}</p>}
      {success && <p className="text-sm text-emerald-600">Gemini key connected.</p>}
      <form action={connectGeminiAction} className="flex w-full max-w-sm flex-col gap-2">
        <input
          type="password"
          name="api_key"
          placeholder="Gemini API key"
          required
          className="rounded border bg-background px-2 py-1 text-sm"
        />
        <Button type="submit">Save</Button>
      </form>
    </main>
  );
}
