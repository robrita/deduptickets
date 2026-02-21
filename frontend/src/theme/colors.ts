/**
 * Centralized color style maps for badges and status indicators.
 *
 * Import these instead of defining inline maps in each component.
 * All values are Tailwind utility class strings.
 */

/** Ticket / merge operation status badges */
export const statusStyles: Record<string, string> = {
  open:        'bg-primary-50 text-primary-700',
  in_progress: 'bg-yellow-100 text-yellow-800',
  resolved:    'bg-green-100 text-green-800',
  closed:      'bg-gray-100 text-gray-800',
  merged:      'bg-primary-100 text-primary-800',
  completed:   'bg-green-100 text-green-800',
  reverted:    'bg-gray-100 text-gray-800',
  pending:     'bg-yellow-100 text-yellow-800',
  dismissed:   'bg-gray-100 text-gray-800',
  expired:     'bg-gray-100 text-gray-500',
};

/** Ticket priority badges */
export const priorityStyles: Record<string, string> = {
  low:    'bg-gray-100 text-gray-800',
  medium: 'bg-primary-50 text-primary-700',
  high:   'bg-orange-100 text-orange-800',
  urgent: 'bg-red-100 text-red-800',
};

/** Severity badges (S1–S4) */
export const severityStyles: Record<string, string> = {
  s4: 'bg-gray-100 text-gray-700',
  s3: 'bg-primary-50 text-primary-700',
  s2: 'bg-orange-100 text-orange-700',
  s1: 'bg-red-100 text-red-700',
};

/** Confidence level styles */
export const confidenceStyles: Record<string, string> = {
  high:   'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low:    'bg-red-100 text-red-700',
};

/** Merge status display labels */
export const mergeStatusLabels: Record<string, string> = {
  completed: 'Merged',
  reverted:  'Reverted',
  pending:   'Pending',
};
