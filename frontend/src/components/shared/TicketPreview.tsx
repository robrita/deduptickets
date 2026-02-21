/**
 * TicketPreview component.
 *
 * Compact ticket display for cluster member lists.
 */

import type { Ticket } from '../../types';
import { severityStyles } from '../../theme/colors';

export interface TicketPreviewProps {
  ticket: Ticket;
  isCanonical?: boolean;
  isSelected?: boolean;
  onSelect?: (ticketId: string) => void;
}

const severityLabels: Record<string, string> = {
  s1: 'S1 - Critical',
  s2: 'S2 - High',
  s3: 'S3 - Medium',
  s4: 'S4 - Low',
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function TicketPreview({
  ticket,
  isCanonical = false,
  isSelected = false,
  onSelect,
}: TicketPreviewProps) {
  const handleClick = () => {
    if (onSelect) {
      onSelect(ticket.id);
    }
  };

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        isSelected
          ? 'border-primary-500 bg-primary-50'
          : isCanonical
            ? 'border-green-500 bg-green-50'
            : 'border-gray-200 bg-white hover:border-gray-300'
      } ${onSelect ? 'cursor-pointer' : ''}`}
      onClick={handleClick}
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onKeyDown={onSelect ? e => e.key === 'Enter' && handleClick() : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="truncate font-medium text-gray-900">{ticket.summary}</h4>
            {isCanonical && (
              <span className="flex-shrink-0 rounded bg-green-500 px-1.5 py-0.5 text-xs font-medium text-white">
                Primary
              </span>
            )}
          </div>

          <p className="mt-1 line-clamp-2 text-sm text-gray-600">{ticket.description}</p>

          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            {ticket.severity && (
              <>
                <span
                  className={`rounded px-1.5 py-0.5 ${severityStyles[ticket.severity] || 'bg-gray-100 text-gray-700'}`}
                >
                  {severityLabels[ticket.severity] || ticket.severity}
                </span>
                <span>•</span>
              </>
            )}
            <span>{ticket.channel}</span>
            <span>•</span>
            <span>{ticket.ticketNumber}</span>
            <span>•</span>
            <span>{formatDate(ticket.createdAt)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TicketPreview;
