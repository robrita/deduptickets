/**
 * ClustersPage component.
 *
 * Main page for viewing and managing duplicate ticket clusters.
 */

import { useState } from 'react';
import { useClusters } from '../hooks/useClusters';
import { ClusterList } from '../components/clusters/ClusterList';
import { ClusterDetail } from '../components/clusters/ClusterDetail';
import { ConfirmDialog } from '../components/shared/ConfirmDialog';

interface ClustersPageProps {
  month: string;
}

export function ClustersPage({ month }: ClustersPageProps) {
  const {
    clusters,
    selectedCluster,
    pendingCount,
    isLoading,
    isLoadingDetail,
    error,
    selectCluster,
    dismissCluster,
    mergeCluster,
    removeTicketFromCluster,
    refresh,
    setFilters,
  } = useClusters(month);

  const [dismissTarget, setDismissTarget] = useState<string | null>(null);
  const [removeTicketTarget, setRemoveTicketTarget] = useState<string | null>(null);
  const [isConfirmProcessing, setIsConfirmProcessing] = useState(false);

  const handleClusterClick = (clusterId: string) => {
    selectCluster(clusterId);
  };

  const handleDismiss = (clusterId: string) => {
    setDismissTarget(clusterId);
  };

  const handleDismissConfirm = async (reason?: string) => {
    if (!dismissTarget) return;
    setIsConfirmProcessing(true);
    try {
      await dismissCluster(dismissTarget, reason || undefined);
      setDismissTarget(null);
    } finally {
      setIsConfirmProcessing(false);
    }
  };

  const handleMerge = async (canonicalTicketId: string) => {
    await mergeCluster(canonicalTicketId);
  };

  const handleRemoveTicket = (ticketId: string) => {
    setRemoveTicketTarget(ticketId);
  };

  const handleRemoveTicketConfirm = async () => {
    if (!removeTicketTarget) return;
    setIsConfirmProcessing(true);
    try {
      await removeTicketFromCluster(removeTicketTarget);
      setRemoveTicketTarget(null);
    } finally {
      setIsConfirmProcessing(false);
    }
  };

  const handleClose = () => {
    selectCluster(null);
  };

  const handleFilterChange = (filters: { status?: string }) => {
    setFilters({
      status: filters.status as 'pending' | 'merged' | 'dismissed' | undefined,
    });
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Duplicate Clusters</h1>
              <p className="mt-1 text-sm text-gray-500">
                Review and merge duplicate support tickets
              </p>
            </div>

            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-yellow-100 px-4 py-2 text-center">
                <p className="text-2xl font-bold text-yellow-800">{pendingCount}</p>
                <p className="text-xs text-yellow-600">Pending Review</p>
              </div>

              <button
                onClick={refresh}
                disabled={isLoading}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="mx-auto max-w-7xl px-4 pt-4 sm:px-6 lg:px-8">
          <div className="rounded-md bg-red-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="mt-1 text-sm text-red-700">{error.message}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex gap-6 transition-all duration-200">
          {/* Cluster list */}
          <div
            className={`transition-all duration-200 ${selectedCluster ? 'w-1/2' : 'w-full'}`}
          >
            <ClusterList
              clusters={clusters}
              isLoading={isLoading}
              compact={Boolean(selectedCluster)}
              selectedClusterId={selectedCluster?.id ?? null}
              onClusterClick={handleClusterClick}
              onDismiss={handleDismiss}
              onFilterChange={handleFilterChange}
            />
          </div>

          {/* Cluster detail panel */}
          {selectedCluster && (
            <div className="w-1/2 transition-all duration-200">
              <div className="sticky top-6 rounded-lg border border-gray-200 bg-white shadow-lg">
                {isLoadingDetail ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
                  </div>
                ) : (
                  <ClusterDetail
                    cluster={selectedCluster}
                    onMerge={handleMerge}
                    onDismiss={() => handleDismiss(selectedCluster.id)}
                    onRemoveTicket={handleRemoveTicket}
                    onClose={handleClose}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Dismiss confirmation dialog */}
      <ConfirmDialog
        isOpen={dismissTarget !== null}
        title="Dismiss Cluster"
        message="Are you sure you want to dismiss this cluster? Dismissed clusters will no longer appear in the pending review queue."
        confirmLabel="Dismiss"
        variant="warning"
        isLoading={isConfirmProcessing}
        reasonLabel="Reason for dismissal (optional)"
        reasonPlaceholder="Explain why this cluster is being dismissed..."
        onConfirm={handleDismissConfirm}
        onCancel={() => setDismissTarget(null)}
      />

      {/* Remove ticket confirmation dialog */}
      <ConfirmDialog
        isOpen={removeTicketTarget !== null}
        title="Remove Ticket"
        message="Are you sure you want to remove this ticket from the cluster? The ticket will no longer be grouped with these duplicates."
        confirmLabel="Remove"
        variant="danger"
        isLoading={isConfirmProcessing}
        onConfirm={handleRemoveTicketConfirm}
        onCancel={() => setRemoveTicketTarget(null)}
      />
    </div>
  );
}

export default ClustersPage;
