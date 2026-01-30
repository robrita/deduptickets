/**
 * ConfidenceBadge component.
 *
 * Displays confidence level with appropriate styling.
 */

import type { ConfidenceLevel } from '../../types';

export interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  size?: 'sm' | 'md' | 'lg';
}

const levelStyles: Record<ConfidenceLevel, { bg: string; label: string }> = {
  high: { bg: 'bg-green-100 text-green-800 border-green-200', label: 'High' },
  medium: { bg: 'bg-yellow-100 text-yellow-800 border-yellow-200', label: 'Medium' },
  low: { bg: 'bg-red-100 text-red-800 border-red-200', label: 'Low' },
};

const sizeStyles = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-1',
  lg: 'text-base px-3 py-1.5',
};

export function ConfidenceBadge({ level, size = 'md' }: ConfidenceBadgeProps) {
  const style = levelStyles[level];

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium ${style.bg} ${sizeStyles[size]}`}
    >
      {style.label}
    </span>
  );
}

export default ConfidenceBadge;
