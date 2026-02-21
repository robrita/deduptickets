/**
 * Ticket service for API interactions.
 *
 * Provides methods for listing and viewing tickets.
 */

import { api } from './api';
import type { Ticket, TicketFilters, PaginatedResponse } from '../types';

export interface TicketListParams extends TicketFilters {
  page?: number;
  page_size?: number;
}

/**
 * List tickets with optional filtering, sorting, and pagination.
 */
export async function listTickets(params: TicketListParams): Promise<PaginatedResponse<Ticket>> {
  const {
    month,
    page = 1,
    page_size = 20,
    status,
    unassigned_only,
    sort_by = 'createdAt',
    sort_order = 'desc',
  } = params;
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.get<PaginatedResponse<Ticket>>('/tickets', {
    params: {
      month: currentMonth,
      page,
      page_size,
      status,
      unassigned_only,
      sort_by,
      sort_order,
    },
  });
}

/**
 * Get a single ticket by ID.
 */
export async function getTicket(
  ticketId: string,
  month?: string
): Promise<Ticket> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.get<Ticket>(`/tickets/${ticketId}`, {
    params: { month: currentMonth },
  });
}

export const ticketService = {
  list: listTickets,
  get: getTicket,
};

export default ticketService;
