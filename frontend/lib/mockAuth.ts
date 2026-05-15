export type AppAuthState =
  | "UNINITIALIZED"
  | "LOCKED"
  | "UNLOCKING"
  | "UNLOCKED"
  | "SESSION_EXPIRED";

const STORAGE_KEY = "taxai_mock_auth_v1";
const SESSION_MS = 15 * 60 * 1000;

interface MockAuthStore {
  initialized: boolean;
  passwordHint?: string;
  recoveryKey?: string;
  sessionExpiresAt?: number;
}

function readStore(): MockAuthStore {
  if (typeof window === "undefined") return { initialized: false };
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return { initialized: false };
  try {
    return JSON.parse(raw) as MockAuthStore;
  } catch {
    return { initialized: false };
  }
}

function writeStore(next: MockAuthStore) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function getInitialAuthState(): AppAuthState {
  const store = readStore();
  if (!store.initialized) return "UNINITIALIZED";
  if (!store.sessionExpiresAt) return "LOCKED";
  if (Date.now() > store.sessionExpiresAt) return "SESSION_EXPIRED";
  return "UNLOCKED";
}

export function createMasterPassword(password: string) {
  const store = readStore();
  // TODO(phase-3-security): Replace placeholder persistence with backend auth + secure hash storage.
  writeStore({
    ...store,
    initialized: true,
    passwordHint: password.slice(0, 2),
    recoveryKey: generateRecoveryKey(),
    sessionExpiresAt: undefined,
  });
}

export function getRecoveryKey(): string {
  const store = readStore();
  return store.recoveryKey || "";
}

export function confirmRecoveryKey(input: string): boolean {
  const store = readStore();
  return !!store.recoveryKey && input.trim() === store.recoveryKey;
}

export async function unlockWorkspace(password: string): Promise<boolean> {
  const store = readStore();
  // TODO(phase-3-security): Placeholder only. Do not use this in production security logic.
  const ok = !!store.passwordHint && password.slice(0, 2) === store.passwordHint;
  if (!ok) return false;
  writeStore({ ...store, sessionExpiresAt: Date.now() + SESSION_MS });
  return true;
}

export function expireSessionNow() {
  const store = readStore();
  writeStore({ ...store, sessionExpiresAt: Date.now() - 1 });
}

export function lockWorkspace() {
  const store = readStore();
  writeStore({ ...store, sessionExpiresAt: undefined });
}

function generateRecoveryKey(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let s = "";
  for (let i = 0; i < 24; i++) s += alphabet[Math.floor(Math.random() * alphabet.length)];
  return `${s.slice(0, 6)}-${s.slice(6, 12)}-${s.slice(12, 18)}-${s.slice(18, 24)}`;
}
