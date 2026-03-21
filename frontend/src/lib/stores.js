import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

function createThemeStore() {
  const stored = browser ? localStorage.getItem('ose_theme') : null;
  const { subscribe, set } = writable(stored || 'parchment');
  return {
    subscribe,
    set(val) {
      if (browser) localStorage.setItem('ose_theme', val);
      set(val);
    },
    toggle() {
      let current;
      subscribe(v => current = v)();
      this.set(current === 'parchment' ? 'notebook' : 'parchment');
    },
  };
}

export const theme = createThemeStore();

function createTokenStore() {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('ose_token') : null;
  const { subscribe, set } = writable(stored);
  return {
    subscribe,
    set(val) {
      if (val) localStorage.setItem('ose_token', val);
      else localStorage.removeItem('ose_token');
      set(val);
    },
    clear() {
      isAdmin.set(null);
      this.set(null);
    },
  };
}

export const token = createTokenStore();
export const isLoggedIn = derived(token, ($t) => !!$t);

/** Admin status: null = unknown, false = not admin, true = admin */
export const isAdmin = writable(null);

/** Fetch user info from /api/auth/me and set isAdmin. Call once on login. */
export async function fetchUserInfo() {
  const t = get(token);
  if (!t) return;
  try {
    const res = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (res.ok) {
      const user = await res.json();
      isAdmin.set(!!user.is_admin);
    }
  } catch {
    // Silently fail — isAdmin stays null
  }
}
