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
    <div className="page-container !max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="page-title">Merge Details</h1>
          <p className="page-subtitle">Review merge operation metadata and ticket relationships.</p>
        </div>
        <button onClick={() => navigate('/merges')} className="btn-secondary">
          Back to Merges
        </button>
      </div>

      <div>
        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
              Loading merge details...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-md bg-red-50 p-4 dark:bg-red-900/30">
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        ) : merge ? (
          <div className="bg-white rounded-lg border border-navy-200 shadow-sm p-6 space-y-6 dark:bg-[var(--color-surface-card)] dark:border-[var(--color-border)]">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-navy-900 dark:text-[var(--color-text)]">
                Operation {merge.id}
              </h2>
              <span
                className={`badge ${
                  merge.status === 'completed' ? 'badge-success' : 'badge-neutral'
                }`}
              >
                {merge.status}
              </span>
            </div>

            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Cluster ID
                </dt>
                <dd className="text-navy-900 break-all dark:text-[var(--color-text)]">
                  {merge.clusterId}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Primary Ticket
                </dt>
                <dd className="text-navy-900 break-all dark:text-[var(--color-text)]">
                  {merge.primaryTicketId}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Merge Behavior
                </dt>
                <dd className="text-navy-900 dark:text-[var(--color-text)]">
                  {merge.mergeBehavior}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Performed By
                </dt>
                <dd className="text-navy-900 dark:text-[var(--color-text)]">{merge.performedBy}</dd>
              </div>
              <div>
                <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Performed At
                </dt>
                <dd className="text-navy-900 dark:text-[var(--color-text)]">
                  {formatDate(merge.performedAt)}
                </dd>
              </div>
              {merge.revertDeadline && (
                <div>
                  <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                    Revert Deadline
                  </dt>
                  <dd className="text-navy-900 dark:text-[var(--color-text)]">
                    {formatDate(merge.revertDeadline)}
                  </dd>
                </div>
              )}
              {merge.revertedAt && (
                <div>
                  <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                    Reverted At
                  </dt>
                  <dd className="text-navy-900 dark:text-[var(--color-text)]">
                    {formatDate(merge.revertedAt)}
                  </dd>
                </div>
              )}
              {merge.revertedBy && (
                <div>
                  <dt className="font-medium text-navy-600 dark:text-[var(--color-text-secondary)]">
                    Reverted By
                  </dt>
                  <dd className="text-navy-900 dark:text-[var(--color-text)]">
                    {merge.revertedBy}
                  </dd>
                </div>
              )}
            </dl>

            <div>
              <h3 className="text-sm font-medium text-navy-700 mb-2 dark:text-[var(--color-text-secondary)]">
                Secondary Tickets
              </h3>
              {merge.secondaryTicketIds.length === 0 ? (
                <p className="text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
                  No secondary tickets.
                </p>
              ) : (
                <ul className="space-y-1">
                  {merge.secondaryTicketIds.map(ticketId => (
                    <li
                      key={ticketId}
                      className="text-sm text-navy-900 bg-navy-50 border border-navy-200 rounded px-3 py-2 break-all dark:text-[var(--color-text)] dark:bg-[var(--color-surface-alt)] dark:border-[var(--color-border)]"
                    >
                      {ticketId}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {merge.revertReason && (
              <div>
                <h3 className="text-sm font-medium text-navy-700 mb-2 dark:text-[var(--color-text-secondary)]">
                  Revert Reason
                </h3>
                <p className="text-sm text-navy-900 bg-navy-50 border border-navy-200 rounded px-3 py-2 dark:text-[var(--color-text)] dark:bg-[var(--color-surface-alt)] dark:border-[var(--color-border)]">
                  {merge.revertReason}
                </p>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default MergeDetailPage;
