/**
 * AuditLog component displays audit entries with filters and pagination.
 */

import type { AuditEntry, AuditFilters } from '../../types';

interface AuditLogProps {
  entries: AuditEntry[];
  isLoading?: boolean;
  filters: AuditFilters;
  onFilterChange: (key: keyof AuditFilters, value: string) => void;
  onEntryClick?: (entry: AuditEntry) => void;
}

const RESOURCE_TYPES = ['ticket', 'cluster', 'merge', 'spike'];
const ACTION_TYPES = [
  'merge',
  'revert',
  'cluster_create',
  'cluster_dismiss',
  'cluster_member_remove',
  'ticket_create',
  'ticket_update',
  'spike_detect',
  'spike_acknowledge',
  'spike_resolve',
];

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getActionColor(action: string): string {
  if (action.includes('create') || action.includes('detect')) {
    return 'bg-blue-100 text-blue-800';
  }
  if (action === 'merge') {
    return 'bg-green-100 text-green-800';
  }
  if (action.includes('revert') || action.includes('dismiss')) {
    return 'bg-orange-100 text-orange-800';
  }
  if (action.includes('resolve') || action.includes('acknowledge')) {
    return 'bg-purple-100 text-purple-800';
  }
  return 'bg-gray-100 text-gray-800';
}

function getResourceIcon(resourceType: string): string {
  switch (resourceType.toLowerCase()) {
    case 'ticket':
      return '🎫';
    case 'cluster':
      return '📦';
    case 'merge':
      return '🔗';
    case 'spike':
      return '📈';
    default:
      return '📝';
  }
}

export function AuditLog({
  entries,
  isLoading,
  filters,
  onFilterChange,
  onEntryClick,
}: AuditLogProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Filters */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Resource Type</label>
            <select
              value={filters.resource_type || ''}
              onChange={e => onFilterChange('resource_type', e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Types</option>
              {RESOURCE_TYPES.map(t => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">Action Type</label>
            <select
              value={filters.action_type || ''}
              onChange={e => onFilterChange('action_type', e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Actions</option>
              {ACTION_TYPES.map(a => (
                <option key={a} value={a}>
                  {a.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">Actor</label>
            <input
              type="text"
              value={filters.actor_id || ''}
              onChange={e => onFilterChange('actor_id', e.target.value)}
              placeholder="Actor ID..."
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Entry List */}
      <div className="divide-y divide-gray-100">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-3 text-gray-500">Loading audit entries...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No audit entries found</div>
        ) : (
          entries.map(entry => (
            <div
              key={entry.id}
              className={`p-4 flex items-start gap-4 ${
                onEntryClick ? 'hover:bg-gray-50 cursor-pointer' : ''
              }`}
              onClick={() => onEntryClick?.(entry)}
            >
              {/* Icon */}
              <span className="text-2xl">{getResourceIcon(entry.resource_type)}</span>

              {/* Main Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${getActionColor(
                      entry.action_type
                    )}`}
                  >
                    {entry.action_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-sm text-gray-500">on {entry.resource_type}</span>
                </div>

                <p className="text-sm text-gray-700 truncate">
                  Resource:{' '}
                  <code className="text-xs bg-gray-100 px-1 rounded">{entry.resource_id}</code>
                </p>

                {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                      View metadata
                    </summary>
                    <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(entry.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>

              {/* Meta Info */}
              <div className="text-right text-sm">
                <p className="text-gray-600">{entry.actor_id}</p>
                <p className="text-gray-400 text-xs">{formatTimestamp(entry.created_at)}</p>
                {entry.ip_address && <p className="text-gray-300 text-xs">{entry.ip_address}</p>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default AuditLog;
