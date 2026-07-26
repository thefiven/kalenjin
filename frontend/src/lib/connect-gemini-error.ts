const MESSAGES: Record<string, string> = {
  missing_key: "Enter your Gemini API key.",
  invalid_key: "That key doesn't work — check it and try again.",
};

export function connectGeminiErrorMessage(error: string | undefined): string | null {
  if (!error) return null;
  return MESSAGES[error] ?? "Something went wrong — try again.";
}
