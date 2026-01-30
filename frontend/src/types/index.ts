/**
 * Type definitions for DedupTickets frontend.
 * Aligned with OpenAPI contract (contracts/openapi.yaml).
 */

// =============================================================================
// Common Types
// =============================================================================

export interface PaginationMeta {
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// =============================================================================
// Ticket Types
// =============================================================================

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed' | 'merged';
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TicketSeverity = 's1' | 's2' | 's3' | 's4';
export type TicketChannel = 'in_app' | 'chat' | 'email' | 'social' | 'phone';

export interface TicketCreate {
  ticket_number: string;
  customer_id?: string;
  summary: string;
  description?: string;
  status: TicketStatus;
  priority?: TicketPriority;
  severity?: TicketSeverity;
  channel: TicketChannel;
  category: string;
  subcategory?: string;
  region: string;
  city?: string;
  transaction_id?: string;
  amount?: number;
  currency?: string;
  merchant?: string;
  occurred_at?: string;
  created_at: string;
  raw_metadata?: Record<string, unknown>;
}

export interface Ticket extends TicketCreate {
  id: string;
  cluster_id?: string;
  merged_into_id?: string;
  updated_at?: string;
  closed_at?: string;
}

// =============================================================================
// Cluster Types
// =============================================================================

export type ClusterStatus = 'pending' | 'merged' | 'dismissed' | 'expired';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface MatchingSignals {
  exact_matches?: Array<{ field: string; value: string }>;
  time_window?: { start: string; end: string };
  text_similarity?: { score: number; common_terms: string[] };
  field_matches?: Array<{ field: string; value: string }>;
}

export interface Cluster {
  id: string;
  status: ClusterStatus;
  confidence: ConfidenceLevel;
  summary: string;
  matching_signals?: MatchingSignals;
  primary_ticket_id?: string;
  ticket_count: number;
  created_at: string;
  updated_at?: string;
  expires_at?: string;
  created_by?: string;
}

export interface ClusterDetail extends Cluster {
  tickets: Ticket[];
}

// =============================================================================
// Merge Types
// =============================================================================

export type MergeBehavior = 'keep_latest' | 'combine_notes' | 'retain_all';
export type MergeStatus = 'completed' | 'reverted';

export interface MergeRequest {
  cluster_id: string;
  primary_ticket_id: string;
  merge_behavior: MergeBehavior;
}

export interface MergeOperation {
  id: string;
  cluster_id: string;
  primary_ticket_id: string;
  secondary_ticket_ids: string[];
  merge_behavior: MergeBehavior;
  status: MergeStatus;
  performed_by: string;
  performed_at: string;
  reverted_at?: string;
  reverted_by?: string;
  revert_reason?: string;
  revert_deadline?: string;
}

export interface RevertConflict {
  ticket_id: string;
  field: string;
  original_value?: string;
  current_value?: string;
}

export interface RevertConflictResponse {
  error: string;
  message: string;
  conflicts: RevertConflict[];
}

// =============================================================================
// Spike Types
// =============================================================================

export type SpikeStatus = 'active' | 'acknowledged' | 'resolved';
export type SeverityLevel = 'low' | 'medium' | 'high';

export interface SpikeAlert {
  id: string;
  status: SpikeStatus;
  severity: SeverityLevel;
  field_name: string;
  field_value: string;
  region?: string;
  current_count: number;
  baseline_count: number;
  percentage_increase: number;
  time_window_start?: string;
  time_window_end?: string;
  detected_at: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

export interface SpikeDetail extends SpikeAlert {
  affected_clusters: Cluster[];
}

// =============================================================================
// Trend Types
// =============================================================================

export type TrendDirection = 'up' | 'down' | 'stable';

export interface Driver {
  id: string;
  theme_summary: string;
  field_name?: string;
  field_value?: string;
  matching_pattern?: Record<string, unknown>;
  cluster_count: number;
  ticket_count: number;
  avg_tickets_per_cluster?: number;
  duplication_rate?: number;
  week_over_week_growth?: number;
  trend_direction?: TrendDirection;
  trend_percentage?: number;
  last_seen_at?: string;
}

export interface TopDriversResponse {
  drivers: Driver[];
  total_clusters: number;
  period: string;
}

export interface GrowingDriversResponse {
  drivers: Driver[];
  compare_period: string;
}

export interface DuplicatedDriversResponse {
  drivers: Driver[];
  avg_duplication_ratio: number;
  period: string;
}

// =============================================================================
// Audit Types
// =============================================================================

export type AuditActionType =
  | 'merge'
  | 'revert'
  | 'cluster_create'
  | 'cluster_dismiss'
  | 'cluster_member_remove'
  | 'ticket_create'
  | 'ticket_update'
  | 'spike_detect'
  | 'spike_acknowledge'
  | 'spike_resolve';

export type ActorType = 'user' | 'system';
export type AuditOutcome = 'success' | 'failure';

export interface AuditEntry {
  id: string;
  action_type: AuditActionType;
  actor_id: string;
  actor_type: ActorType;
  resource_type: string;
  resource_id: string;
  related_ids?: string[];
  metadata?: Record<string, unknown>;
  outcome: AuditOutcome;
  error_message?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

// =============================================================================
// Filter Types
// =============================================================================

export interface ClusterFilters {
  status?: ClusterStatus;
  confidence?: ConfidenceLevel;
  min_confidence?: number;
  min_ticket_count?: number;
  region?: string;
  month?: string;
}

export interface TicketFilters {
  status?: TicketStatus;
  channel?: TicketChannel;
  category?: string;
  merchant?: string;
  region?: string;
  created_after?: string;
  created_before?: string;
}

export interface SpikeFilters {
  status?: SpikeStatus;
  severity?: SeverityLevel;
  field_name?: string;
  detected_after?: string;
  active_only?: boolean;
  region?: string;
  month?: string;
  product?: string;
}

export interface AuditFilters {
  action_type?: AuditActionType;
  actor_id?: string;
  resource_type?: string;
  resource_id?: string;
  created_after?: string;
  created_before?: string;
}

export interface TrendFilters {
  period?: 'day' | 'week' | 'month';
  limit?: number;
  region?: string;
  field_name?: string;
  days?: number;
}
