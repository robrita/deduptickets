/**
 * AuditPage with search interface for audit log.
 */

import { useEffect, useState, useCallback } from 'react';
import type { AuditEntry, AuditFilters } from '../types';
import { listAuditEntries } from '../services/auditService';
import { AuditLog } from '../components/audit/AuditLog';

export function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 20;

  // Filters
  const [filters, setFilters] = useState<AuditFilters>({});

  // Advanced search state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advancedSearch, setAdvancedSearch] = useState<AuditFilters>({});

  const fetchEntries = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listAuditEntries(filters, page, pageSize);
      setEntries(response.data);
      setTotalItems(response.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit entries');
    } finally {
      setIsLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleFilterChange = (key: keyof AuditFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
    setPage(1);
  };

  const handleAdvancedSearch = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listAuditEntries(advancedSearch, page, pageSize);
      setEntries(response.data);
      setTotalItems(response.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEntryClick = (entry: AuditEntry) => {
    // For now, just log to console - could open a detail modal
    console.log('Audit entry clicked:', entry);
  };

  const totalPages = Math.ceil(totalItems / pageSize);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
            <p className="text-gray-500">
              Complete action history for compliance and investigation
            </p>
          </div>

          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {showAdvanced ? 'Simple Search' : 'Advanced Search'}
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-600">Entries Shown</p>
            <p className="text-3xl font-bold text-blue-700">{entries.length}</p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600">Total Matching</p>
            <p className="text-3xl font-bold text-gray-700">{totalItems}</p>
          </div>
        </div>

        {/* Advanced Search Panel */}
        {showAdvanced && (
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-medium text-gray-900 mb-4">Advanced Search</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Resource Type</label>
                <input
                  type="text"
                  value={advancedSearch.resource_type || ''}
                  onChange={e =>
                    setAdvancedSearch(prev => ({
                      ...prev,
                      resource_type: e.target.value || undefined,
                    }))
                  }
                  placeholder="ticket, cluster, etc."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Resource ID</label>
                <input
                  type="text"
                  value={advancedSearch.resource_id || ''}
                  onChange={e =>
                    setAdvancedSearch(prev => ({
                      ...prev,
                      resource_id: e.target.value || undefined,
                    }))
                  }
                  placeholder="UUID"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Actor ID</label>
                <input
                  type="text"
                  value={advancedSearch.actor_id || ''}
                  onChange={e =>
                    setAdvancedSearch(prev => ({
                      ...prev,
                      actor_id: e.target.value || undefined,
                    }))
                  }
                  placeholder="User or System"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Created After</label>
                <input
                  type="datetime-local"
                  value={advancedSearch.created_after || ''}
                  onChange={e =>
                    setAdvancedSearch(prev => ({
                      ...prev,
                      created_after: e.target.value || undefined,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Created Before</label>
                <input
                  type="datetime-local"
                  value={advancedSearch.created_before || ''}
                  onChange={e =>
                    setAdvancedSearch(prev => ({
                      ...prev,
                      created_before: e.target.value || undefined,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleAdvancedSearch}
                  className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Search
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
            <button onClick={() => setError(null)} className="ml-4 text-red-500 hover:text-red-700">
              Dismiss
            </button>
          </div>
        )}

        {/* Audit Log Component */}
        <AuditLog
          entries={entries}
          isLoading={isLoading}
          filters={filters}
          onFilterChange={handleFilterChange}
          onEntryClick={handleEntryClick}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-gray-600">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default AuditPage;
