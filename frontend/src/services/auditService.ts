/**
 * Service for audit log API operations.
 */

import { api } from './api';
import type { AuditEntry, AuditFilters, PaginatedResponse } from '../types';

/**
 * List audit entries with optional filtering.
 */
export async function listAuditEntries(
  filters: AuditFilters = {},
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<AuditEntry>> {
  const params = new URLSearchParams();
  params.set('offset', ((page - 1) * pageSize).toString());
  params.set('limit', pageSize.toString());

  if (filters.resource_type) params.set('resource_type', filters.resource_type);
  if (filters.resource_id) params.set('resource_id', filters.resource_id);
  if (filters.actor_id) params.set('actor_id', filters.actor_id);
  if (filters.action_type) params.set('action_type', filters.action_type);
  if (filters.created_after) params.set('created_after', filters.created_after);
  if (filters.created_before) params.set('created_before', filters.created_before);

  return api.get<PaginatedResponse<AuditEntry>>(`/audit?${params.toString()}`);
}

/**
 * Get a specific audit entry by ID.
 */
export async function getAuditEntry(auditId: string): Promise<AuditEntry> {
  return api.get<AuditEntry>(`/audit/${auditId}`);
}

/**
 * Get audit history for a specific resource.
 */
export async function getResourceHistory(
  resourceType: string,
  resourceId: string,
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<AuditEntry>> {
  const params = new URLSearchParams({
    resource_type: resourceType,
    resource_id: resourceId,
    offset: ((page - 1) * pageSize).toString(),
    limit: pageSize.toString(),
  });

  return api.get<PaginatedResponse<AuditEntry>>(`/audit?${params.toString()}`);
}
