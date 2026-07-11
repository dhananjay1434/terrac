// Portal session token store. The opaque bearer token from POST /login lives in
// localStorage; every API call attaches it. A 401 clears it and bounces to login.
const TOKEN_KEY = "dmrv.portal.token";
const ROLE_KEY = "dmrv.portal.role";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole(): string | null {
  return localStorage.getItem(ROLE_KEY);
}

export function setSession(token: string, role: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function isAuthed(): boolean {
  return !!getToken();
}
