/**
 * MergesPage component.
 *
 * Main page for viewing merge history and reverting merges.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { MergeHistoryItem } from '../components/merges/MergeHistoryItem';
import { RevertConfirmDialog } from '../components/merges/RevertConfirmDialog';
import type { MergeOperation, RevertConflict } from '../types';
import { mergeService } from '../services/mergeService';

type FilterStatus = 'all' | 'completed' | 'reverted' | 'revertible';

export const MergesPage: React.FC = () => {
  const [merges, setMerges] = useState<MergeOperation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  // Revert dialog state
  const [selectedMerge, setSelectedMerge] = useState<MergeOperation | null>(null);
  const [conflicts, setConflicts] = useState<RevertConflict[] | null>(null);
  const [isReverting, setIsReverting] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Get partition key from URL or defaults
  const region = new URLSearchParams(window.location.search).get('region') || 'US';
  const month =
    new URLSearchParams(window.location.search).get('month') ||
    new Date().toISOString().slice(0, 7);

  const loadMerges = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const revertibleOnly = filterStatus === 'revertible';
      const data = await mergeService.listMerges(region, month, 1, 50, revertibleOnly);

      let filtered = data.data;
      if (filterStatus === 'completed') {
        filtered = data.data.filter(m => m.status === 'completed');
      } else if (filterStatus === 'reverted') {
        filtered = data.data.filter(m => m.status === 'reverted');
      }

      setMerges(filtered);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load merges');
    } finally {
      setIsLoading(false);
    }
  }, [region, month, filterStatus]);

  useEffect(() => {
    loadMerges();
  }, [loadMerges]);

  const handleRevertClick = async (merge: MergeOperation) => {
    setSelectedMerge(merge);
    setIsDialogOpen(true);

    // Check for conflicts
    try {
      const conflictCheck = await mergeService.checkRevertConflicts(merge.id, region, month);
      setConflicts(conflictCheck);
    } catch (err) {
      // If conflict check fails, still show dialog without conflict info
      setConflicts(null);
    }
  };

  const handleRevertConfirm = async (reason: string) => {
    if (!selectedMerge) return;

    setIsReverting(true);
    try {
      await mergeService.revertMerge(selectedMerge.id, region, month, reason);
      setIsDialogOpen(false);
      setSelectedMerge(null);
      setConflicts(null);
      // Reload the list
      await loadMerges();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revert merge');
    } finally {
      setIsReverting(false);
    }
  };

  const handleRevertCancel = () => {
    setIsDialogOpen(false);
    setSelectedMerge(null);
    setConflicts(null);
  };

  const handleViewDetails = (merge: MergeOperation) => {
    // Navigate to merge detail view
    window.location.href = `/merges/${merge.id}?region=${region}&month=${month}`;
  };

  const filterOptions: { value: FilterStatus; label: string }[] = [
    { value: 'all', label: 'All Merges' },
    { value: 'completed', label: 'Completed' },
    { value: 'reverted', label: 'Reverted' },
    { value: 'revertible', label: 'Revertible Only' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Merge History</h1>
              <p className="mt-1 text-sm text-gray-500">
                View and manage merge operations. Revert merges within 24 hours.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">
                Region: {region} | Month: {month}
              </span>
              <button
                onClick={loadMerges}
                disabled={isLoading}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <svg
                  className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="mb-6">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Filter:</span>
            <div className="flex rounded-md shadow-sm">
              {filterOptions.map(option => (
                <button
                  key={option.value}
                  onClick={() => setFilterStatus(option.value)}
                  className={`px-4 py-2 text-sm font-medium border ${
                    filterStatus === option.value
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  } ${
                    option.value === 'all'
                      ? 'rounded-l-md'
                      : option.value === 'revertible'
                        ? 'rounded-r-md'
                        : ''
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 rounded-md bg-red-50 p-4">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="ml-3 text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Loading state */}
        {isLoading ? (
          <div className="text-center py-12">
            <svg
              className="animate-spin h-8 w-8 mx-auto text-indigo-600"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <p className="mt-2 text-sm text-gray-500">Loading merges...</p>
          </div>
        ) : merges.length === 0 ? (
          /* Empty state */
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No merge operations</h3>
            <p className="mt-1 text-sm text-gray-500">
              {filterStatus === 'revertible'
                ? 'No revertible merges found.'
                : 'No merge operations found for this period.'}
            </p>
          </div>
        ) : (
          /* Merge list */
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Showing {merges.length} merge{merges.length !== 1 ? 's' : ''}
            </p>
            {merges.map(merge => (
              <MergeHistoryItem
                key={merge.id}
                merge={merge}
                onRevert={handleRevertClick}
                onViewDetails={handleViewDetails}
              />
            ))}
          </div>
        )}
      </main>

      {/* Revert confirmation dialog */}
      {selectedMerge && (
        <RevertConfirmDialog
          merge={selectedMerge}
          conflicts={conflicts}
          isOpen={isDialogOpen}
          isLoading={isReverting}
          onConfirm={handleRevertConfirm}
          onCancel={handleRevertCancel}
        />
      )}
    </div>
  );
};
