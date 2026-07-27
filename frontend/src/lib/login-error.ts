type ErrorKey = "invalidState" | "notInvited" | "googleAuthFailed" | "default";

const ERROR_KEYS: Record<string, ErrorKey> = {
  invalid_state: "invalidState",
  not_invited: "notInvited",
  google_auth_failed: "googleAuthFailed",
};

export function loginErrorKey(error: string | undefined): ErrorKey | null {
  if (!error) return null;
  return ERROR_KEYS[error] ?? "default";
}
