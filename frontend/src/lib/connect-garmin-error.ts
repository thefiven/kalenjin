const MESSAGES: Record<string, string> = {
  missing_fields: "Enter your Garmin email and password.",
  invalid_credentials: "That email or password doesn't work — check it and try again.",
  missing_mfa_code: "Enter the MFA code Garmin sent you.",
  invalid_mfa_code: "That code didn't work, or it expired — start over.",
};

export function connectGarminErrorMessage(error: string | undefined): string | null {
  if (!error) return null;
  return MESSAGES[error] ?? "Something went wrong — try again.";
}
