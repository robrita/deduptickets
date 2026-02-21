/**
 * Type definitions for DedupTickets frontend.
 * Aligned with OpenAPI contract (contracts/openapi.yaml).
 *
 * Field names use camelCase to match API JSON response format.
 */

// =============================================================================
// Common Types
// =============================================================================

export interface PaginationMeta {
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
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
  ticketNumber: string;
  customerId?: string;
  summary: string;
  description?: string;
  status: TicketStatus;
  priority?: TicketPriority;
  severity?: TicketSeverity;
  channel: TicketChannel;
  category: string;
  subcategory?: string;
  transactionId?: string;
  amount?: number;
  currency?: string;
  merchant?: string;
  occurredAt?: string;
  createdAt: string;
  rawMetadata?: Record<string, unknown>;
}

export interface Ticket extends TicketCreate {
  id: string;
  clusterId?: string;
  mergedIntoId?: string;
  updatedAt?: string;
  closedAt?: string;
}

// =============================================================================
// Cluster Types
// =============================================================================

export type ClusterStatus = 'pending' | 'merged' | 'dismissed' | 'expired';

export interface ClusterMember {
  ticketId: string;
  ticketNumber: string;
  addedAt: string;
  summary?: string;
  category?: string;
  subcategory?: string;
  createdAt?: string;
  confidenceScore?: number;
}

export interface Cluster {
  id: string;
  status: ClusterStatus;
  summary: string;
  ticketCount: number;
  createdAt: string;
  updatedAt?: string;
  expiresAt?: string;
  createdBy?: string;
}

export interface ClusterDetail extends Cluster {
  members: ClusterMember[];
}

// =============================================================================
// Merge Types
// =============================================================================

export type MergeBehavior = 'keep_latest' | 'combine_notes' | 'retain_all';
export type MergeStatus = 'completed' | 'reverted';

export interface MergeRequest {
  clusterId: string;
  primaryTicketId: string;
  mergeBehavior: MergeBehavior;
}

export interface MergeOperation {
  id: string;
  clusterId: string;
  primaryTicketId: string;
  secondaryTicketIds: string[];
  mergeBehavior: MergeBehavior;
  status: MergeStatus;
  performedBy: string;
  performedAt: string;
  revertedAt?: string;
  revertedBy?: string;
  revertReason?: string;
  revertDeadline?: string;
}

export interface RevertConflict {
  ticketId: string;
  field: string;
  originalValue?: string;
  currentValue?: string;
}

export interface RevertConflictResponse {
  error: string;
  message: string;
  conflicts: RevertConflict[];
}

// =============================================================================
// Filter Types
// =============================================================================

export interface ClusterFilters {
  status?: ClusterStatus;
  min_ticket_count?: number;
  month?: string;
}

export interface TicketFilters {
  status?: TicketStatus;
  channel?: TicketChannel;
  category?: string;
  merchant?: string;
  month?: string;
  created_after?: string;
  created_before?: string;
  unassigned_only?: boolean;
  sort_by?: 'createdAt' | 'priority' | 'status' | 'ticketNumber';
  sort_order?: 'asc' | 'desc';
}
