/**
 * Centralized color style maps for badges and status indicators.
 * GCash official design system — uses navy-* instead of gray-*.
 *
 * Import these instead of defining inline maps in each component.
 * All values are Tailwind utility class strings.
 */

/** Ticket / merge operation status badges */
export const statusStyles: Record<string, string> = {
  open: 'bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300',
  in_progress: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  closed: 'bg-navy-100 text-navy-800 dark:bg-navy-800 dark:text-navy-200',
  merged: 'bg-primary-100 text-primary-800 dark:bg-primary-900/40 dark:text-primary-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  reverted: 'bg-navy-100 text-navy-800 dark:bg-navy-800 dark:text-navy-200',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  dismissed: 'bg-navy-100 text-navy-800 dark:bg-navy-800 dark:text-navy-200',
  expired: 'bg-navy-100 text-navy-600 dark:bg-navy-800 dark:text-navy-400',
};

/** Ticket priority badges */
export const priorityStyles: Record<string, string> = {
  low: 'bg-navy-100 text-navy-800 dark:bg-navy-800 dark:text-navy-200',
  medium: 'bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  urgent: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

/** Severity badges (S1–S4) */
export const severityStyles: Record<string, string> = {
  s4: 'bg-navy-100 text-navy-700 dark:bg-navy-800 dark:text-navy-300',
  s3: 'bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300',
  s2: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  s1: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
};

/** Confidence level styles */
export const confidenceStyles: Record<string, string> = {
  high: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
  low: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
};

/** Merge status display labels */
export const mergeStatusLabels: Record<string, string> = {
  completed: 'Merged',
  reverted: 'Reverted',
  pending: 'Pending',
};
