/** Domain types matching the backend API schemas. */

export type ResilienceZone = 'green' | 'yellow' | 'red';

export interface FeatureScores {
  calendar_density_score: number;
  after_hours_activity_index: number;
  context_switch_count: number;
  sprint_health_index: number;
}

export interface TeamCard {
  team_id: string;
  team_name: string;
  department: string;
  zone: ResilienceZone;
  zone_label: number;
  afs: number;
  features: FeatureScores;
  has_active_alert: boolean;
}

export interface DeptSummary {
  department: string;
  total: number;
  green: number;
  yellow: number;
  red: number;
}

export interface DashboardSummary {
  total_teams: number;
  green: number;
  yellow: number;
  red: number;
  active_alerts: number;
  departments: DeptSummary[];
}

export interface DayPoint {
  date: string;
  afs: number;
  zone: ResilienceZone;
  calendar_density_score: number;
  after_hours_activity_index: number;
  context_switch_count: number;
  sprint_health_index: number;
}

export interface InterventionItem {
  id: string;
  title: string;
  description: string;
}

export interface TeamHistory {
  team_id: string;
  team_name: string;
  department: string;
  zone: ResilienceZone;
  afs: number;
  features: FeatureScores;
  history: DayPoint[];
  interventions: InterventionItem[];
}

export interface AlertRecord {
  alert_id: string;
  team_id: string;
  team_name: string;
  department: string;
  workspace_id: string;
  trigger_date: string;
  consecutive_red_days: number;
  interventions: InterventionItem[];
}

// ── Org history (trend + sparklines) ─────────────────────────────────────────

export interface OrgTrendPoint {
  date: string;
  afs: number;
}

export interface TeamTrendSeries {
  name: string;
  department: string;
  history: OrgTrendPoint[];
}

export interface OrgHistory {
  org: OrgTrendPoint[];
  by_department: Record<string, OrgTrendPoint[]>;
  by_team: Record<string, TeamTrendSeries>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export type UserRole = 'hr_admin' | 'team_manager' | 'viewer';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  /** For team_manager role — the team they can access */
  team_id?: string;
}
