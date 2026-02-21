import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { mergeService } from '../services/mergeService';
import type { MergeOperation } from '../types';

interface MergeDetailPageProps {
  month: string;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const MergeDetailPage: React.FC<MergeDetailPageProps> = ({ month }) => {
  const navigate = useNavigate();
  const { mergeId } = useParams<{ mergeId: string }>();

  const [merge, setMerge] = useState<MergeOperation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadMerge = async () => {
      if (!mergeId) {
        setError('Missing merge id');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const data = await mergeService.getMerge(mergeId, month);
        setMerge(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load merge details');
      } finally {
        setIsLoading(false);
      }
    };

    loadMerge();
  }, [mergeId, month]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Merge Details</h1>
              <p className="mt-1 text-sm text-gray-500">Review merge operation metadata and ticket relationships.</p>
            </div>
            <button
              onClick={() => navigate('/merges')}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Back to Merges
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-sm text-gray-500">Loading merge details...</p>
          </div>
        ) : error ? (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        ) : merge ? (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Operation {merge.id}</h2>
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  merge.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {merge.status}
              </span>
            </div>

            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="font-medium text-gray-500">Cluster ID</dt>
                <dd className="text-gray-900 break-all">{merge.clusterId}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Primary Ticket</dt>
                <dd className="text-gray-900 break-all">{merge.primaryTicketId}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Merge Behavior</dt>
                <dd className="text-gray-900">{merge.mergeBehavior}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Performed By</dt>
                <dd className="text-gray-900">{merge.performedBy}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-500">Performed At</dt>
                <dd className="text-gray-900">{formatDate(merge.performedAt)}</dd>
              </div>
              {merge.revertDeadline && (
                <div>
                  <dt className="font-medium text-gray-500">Revert Deadline</dt>
                  <dd className="text-gray-900">{formatDate(merge.revertDeadline)}</dd>
                </div>
              )}
              {merge.revertedAt && (
                <div>
                  <dt className="font-medium text-gray-500">Reverted At</dt>
                  <dd className="text-gray-900">{formatDate(merge.revertedAt)}</dd>
                </div>
              )}
              {merge.revertedBy && (
                <div>
                  <dt className="font-medium text-gray-500">Reverted By</dt>
                  <dd className="text-gray-900">{merge.revertedBy}</dd>
                </div>
              )}
            </dl>

            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Secondary Tickets</h3>
              {merge.secondaryTicketIds.length === 0 ? (
                <p className="text-sm text-gray-500">No secondary tickets.</p>
              ) : (
                <ul className="space-y-1">
                  {merge.secondaryTicketIds.map(ticketId => (
                    <li
                      key={ticketId}
                      className="text-sm text-gray-900 bg-gray-50 border border-gray-200 rounded px-3 py-2 break-all"
                    >
                      {ticketId}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {merge.revertReason && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Revert Reason</h3>
                <p className="text-sm text-gray-900 bg-gray-50 border border-gray-200 rounded px-3 py-2">
                  {merge.revertReason}
                </p>
              </div>
            )}
          </div>
        ) : null}
      </main>
    </div>
  );
};

export default MergeDetailPage;