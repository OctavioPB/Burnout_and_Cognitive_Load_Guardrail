/**
 * React Query hooks for all backend API endpoints.
 *
 * All requests go through apiClient which attaches auth headers automatically.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/apiClient';
import type {
  AlertRecord,
  DashboardSummary,
  OrgHistory,
  TeamCard,
  TeamHistory,
} from '../types/domain';
import type {
  ApplyInterventionRequest,
  AuditLogEntry,
  DismissInterventionRequest,
  EfficacyView,
  InterventionRecord,
} from '../types/interventions';

// ── Query keys ────────────────────────────────────────────────────────────────

export const queryKeys = {
  summary:     ['dashboard', 'summary']                         as const,
  teams:       (dept?: string) => ['dashboard', 'teams', dept ?? 'all'] as const,
  teamHistory: (teamId: string) => ['teams', teamId, 'history'] as const,
  alerts:      (dept?: string) => ['alerts', dept ?? 'all']     as const,
  teamInterventions: (teamId: string) => ['interventions', teamId] as const,
  efficacy:    (teamId: string, iid: string) => ['interventions', teamId, 'efficacy', iid] as const,
  auditLog:    ['audit'] as const,
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: queryKeys.summary,
    queryFn:  () => apiClient.get<DashboardSummary>('/dashboard/summary').then(r => r.data),
    staleTime: 60_000,
  });
}

export function useTeams(department?: string) {
  return useQuery<TeamCard[]>({
    queryKey: queryKeys.teams(department),
    queryFn:  () =>
      apiClient.get<TeamCard[]>('/dashboard/teams', {
        params: department ? { department } : undefined,
      }).then(r => r.data),
    staleTime: 60_000,
  });
}

export function useTeamHistory(teamId: string) {
  return useQuery<TeamHistory>({
    queryKey: queryKeys.teamHistory(teamId),
    queryFn:  () => apiClient.get<TeamHistory>(`/teams/${teamId}/history`).then(r => r.data),
    staleTime: 60_000,
    enabled:  Boolean(teamId),
  });
}

export function useOrgHistory() {
  return useQuery<OrgHistory>({
    queryKey: ['dashboard', 'org-history'],
    queryFn:  () => apiClient.get<OrgHistory>('/dashboard/org-history').then(r => r.data),
    staleTime: 60_000,
  });
}

export function useAlerts(department?: string) {
  return useQuery<AlertRecord[]>({
    queryKey: queryKeys.alerts(department),
    queryFn:  () =>
      apiClient.get<AlertRecord[]>('/alerts', {
        params: department ? { department } : undefined,
      }).then(r => r.data),
    staleTime: 60_000,
  });
}

// ── Interventions ─────────────────────────────────────────────────────────────

export function useTeamInterventions(teamId: string) {
  return useQuery<InterventionRecord[]>({
    queryKey: queryKeys.teamInterventions(teamId),
    queryFn:  () =>
      apiClient.get<InterventionRecord[]>(`/interventions/${teamId}`).then(r => r.data),
    staleTime: 30_000,
    enabled:  Boolean(teamId),
  });
}

export function useApplyIntervention(teamId: string) {
  const qc = useQueryClient();
  return useMutation<InterventionRecord, Error, ApplyInterventionRequest>({
    mutationFn: body =>
      apiClient.post<InterventionRecord>(`/interventions/${teamId}/apply`, body).then(r => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.teamInterventions(teamId) });
      void qc.invalidateQueries({ queryKey: queryKeys.teamHistory(teamId) });
    },
  });
}

export function useDismissIntervention(teamId: string) {
  const qc = useQueryClient();
  return useMutation<InterventionRecord, Error, DismissInterventionRequest>({
    mutationFn: body =>
      apiClient.post<InterventionRecord>(`/interventions/${teamId}/dismiss`, body).then(r => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.teamInterventions(teamId) });
    },
  });
}

export function useEfficacy(teamId: string, interventionId: string, enabled: boolean) {
  return useQuery<EfficacyView>({
    queryKey: queryKeys.efficacy(teamId, interventionId),
    queryFn:  () =>
      apiClient.get<EfficacyView>(`/interventions/${teamId}/efficacy/${interventionId}`).then(r => r.data),
    staleTime: 120_000,
    enabled:  enabled && Boolean(teamId) && Boolean(interventionId),
  });
}

// ── Audit log ─────────────────────────────────────────────────────────────────

export function useAuditLog(limit = 100) {
  return useQuery<AuditLogEntry[]>({
    queryKey: queryKeys.auditLog,
    queryFn:  () =>
      apiClient.get<AuditLogEntry[]>('/audit', { params: { limit } }).then(r => r.data),
    staleTime: 30_000,
  });
}

// ── Admin (HR Admin only) ─────────────────────────────────────────────────────

export interface AdminTeamEntry {
  team_id: string;
  team_name: string;
  department: string;
}

export interface AdminSeedRequest {
  teams: AdminTeamEntry[];
  stress_profile: 'low' | 'mixed' | 'high';
  history_days: 7 | 14 | 30;
}

export interface AdminActionResponse {
  message: string;
  team_count: number;
}

export function useResetStore() {
  const qc = useQueryClient();
  return useMutation<AdminActionResponse, Error, void>({
    mutationFn: () =>
      apiClient.post<AdminActionResponse>('/admin/reset').then(r => r.data),
    onSuccess: () => { void qc.invalidateQueries(); },
  });
}

export function useSeedStore() {
  const qc = useQueryClient();
  return useMutation<AdminActionResponse, Error, AdminSeedRequest>({
    mutationFn: body =>
      apiClient.post<AdminActionResponse>('/admin/seed', body).then(r => r.data),
    onSuccess: () => { void qc.invalidateQueries(); },
  });
}
