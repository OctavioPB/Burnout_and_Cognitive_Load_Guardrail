/**
 * React Query hooks for dashboard data.
 *
 * All hooks point at VITE_API_URL (defaults to http://localhost:8000).
 * Error objects are re-thrown so the nearest ErrorBoundary catches them.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type {
  AlertRecord,
  DashboardSummary,
  TeamCard,
  TeamHistory,
} from '../types/domain';

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const api = axios.create({ baseURL: BASE });

// ── Keys ──────────────────────────────────────────────────────────────────────

export const queryKeys = {
  summary:     ['dashboard', 'summary'] as const,
  teams:       (dept?: string) => ['dashboard', 'teams', dept ?? 'all'] as const,
  teamHistory: (teamId: string) => ['teams', teamId, 'history'] as const,
  alerts:      (dept?: string) => ['alerts', dept ?? 'all'] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: queryKeys.summary,
    queryFn:  () => api.get<DashboardSummary>('/dashboard/summary').then(r => r.data),
    staleTime: 60_000,
  });
}

export function useTeams(department?: string) {
  return useQuery<TeamCard[]>({
    queryKey: queryKeys.teams(department),
    queryFn:  () =>
      api.get<TeamCard[]>('/dashboard/teams', {
        params: department ? { department } : undefined,
      }).then(r => r.data),
    staleTime: 60_000,
  });
}

export function useTeamHistory(teamId: string) {
  return useQuery<TeamHistory>({
    queryKey: queryKeys.teamHistory(teamId),
    queryFn:  () =>
      api.get<TeamHistory>(`/teams/${teamId}/history`).then(r => r.data),
    staleTime: 60_000,
    enabled: Boolean(teamId),
  });
}

export function useAlerts(department?: string) {
  return useQuery<AlertRecord[]>({
    queryKey: queryKeys.alerts(department),
    queryFn:  () =>
      api.get<AlertRecord[]>('/alerts', {
        params: department ? { department } : undefined,
      }).then(r => r.data),
    staleTime: 60_000,
  });
}
