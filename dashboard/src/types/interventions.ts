/** TypeScript types matching api/schemas/interventions.py. */

export type InterventionAction = 'accepted' | 'dismissed' | 'customized';
export type IntegrationStatus  = 'pending' | 'success' | 'failed' | 'skipped';

export interface IntegrationResult {
  integration: string;
  status: IntegrationStatus;
  external_id: string | null;
  detail: string;
}

export interface InterventionRecord {
  record_id: string;
  team_id: string;
  intervention_id: string;
  intervention_title: string;
  action: InterventionAction;
  actor_id: string;
  actor_name: string;
  applied_at: string;
  customization: string | null;
  integration: IntegrationResult;
}

export interface ApplyInterventionRequest {
  intervention_id: string;
  customization?: string;
}

export interface DismissInterventionRequest {
  intervention_id: string;
}

export type EfficacyPhase = 'before' | 'after';

export interface EfficacyPoint {
  date: string;
  afs: number;
  zone: string;
  phase: EfficacyPhase;
}

export interface EfficacyView {
  team_id: string;
  team_name: string;
  intervention_id: string;
  intervention_title: string;
  applied_at: string;
  before_avg_afs: number;
  after_avg_afs: number;
  has_sufficient_data: boolean;
  points: EfficacyPoint[];
}

export type AuditAction =
  | 'view_dashboard'
  | 'view_team'
  | 'view_alerts'
  | 'view_audit'
  | 'apply_intervention'
  | 'dismiss_intervention';

export interface AuditLogEntry {
  log_id: string;
  actor_id: string;
  actor_name: string;
  actor_role: string;
  action: AuditAction;
  resource: string;
  timestamp: string;
  detail: string;
}
