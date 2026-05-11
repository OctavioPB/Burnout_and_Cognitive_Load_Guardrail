/**
 * Auth state — persisted to localStorage so the session survives page reloads.
 *
 * In production this would be replaced by an Okta/Auth0 PKCE flow that sets
 * a real JWT.  For staging we store the user profile directly in localStorage.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthUser } from '../types/domain';

interface AuthState {
  user: AuthUser | null;
  login: (user: AuthUser) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,

      login: (user) => set({ user }),

      logout: () => set({ user: null }),

      isAuthenticated: () => get().user !== null,
    }),
    { name: 'burnout-guardrail-auth' },
  ),
);
