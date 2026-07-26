const MESSAGES: Record<string, string> = {
  invalid_state: "Something went wrong starting the sign-in flow — please try again.",
  not_invited: "This Google account hasn't been invited to Kalenjin yet.",
  google_auth_failed: "Google couldn't confirm your identity — please try again.",
};

export function loginErrorMessage(error: string | undefined): string | null {
  if (!error) return null;
  return MESSAGES[error] ?? "Something went wrong signing in — please try again.";
}
