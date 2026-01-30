/**
 * ClustersPage component.
 *
 * Main page for viewing and managing duplicate ticket clusters.
 */

import { useClusters } from '../hooks/useClusters';
import { ClusterList } from '../components/clusters/ClusterList';
import { ClusterDetail } from '../components/clusters/ClusterDetail';

export function ClustersPage() {
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
  } = useClusters();

  const handleClusterClick = (clusterId: string) => {
    selectCluster(clusterId);
  };

  const handleDismiss = async (clusterId: string) => {
    const reason = window.prompt('Reason for dismissal (optional):');
    await dismissCluster(clusterId, reason || undefined);
  };

  const handleMerge = async (canonicalTicketId: string) => {
    await mergeCluster(canonicalTicketId);
  };

  const handleRemoveTicket = async (ticketId: string) => {
    if (window.confirm('Remove this ticket from the cluster?')) {
      await removeTicketFromCluster(ticketId);
    }
  };

  const handleClose = () => {
    selectCluster(null);
  };

  const handleFilterChange = (filters: { status?: string; minConfidence?: number }) => {
    setFilters({
      status: filters.status as 'pending' | 'merged' | 'dismissed' | undefined,
      min_confidence: filters.minConfidence,
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
        <div className="flex gap-6">
          {/* Cluster list */}
          <div className={selectedCluster ? 'w-1/2' : 'w-full'}>
            <ClusterList
              clusters={clusters}
              isLoading={isLoading}
              onClusterClick={handleClusterClick}
              onDismiss={handleDismiss}
              onFilterChange={handleFilterChange}
            />
          </div>

          {/* Cluster detail panel */}
          {selectedCluster && (
            <div className="w-1/2">
              <div className="sticky top-6 rounded-lg border border-gray-200 bg-white shadow-lg">
                {isLoadingDetail ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
                  </div>
                ) : (
                  <ClusterDetail
                    cluster={selectedCluster}
                    onMerge={handleMerge}
                    onDismiss={() => dismissCluster(selectedCluster.id)}
                    onRemoveTicket={handleRemoveTicket}
                    onClose={handleClose}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default ClustersPage;
