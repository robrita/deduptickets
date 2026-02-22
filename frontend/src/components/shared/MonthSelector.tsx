import type React from 'react';

interface MonthSelectorProps {
  value: string;
  onChange: (month: string) => void;
}

export const MonthSelector: React.FC<MonthSelectorProps> = ({ value, onChange }) => (
  <div className="flex items-center gap-2">
    <label htmlFor="global-month" className="text-sm font-medium text-navy-600 dark:text-navy-400">
      Month:
    </label>
    <input
      type="month"
      id="global-month"
      value={value}
      onChange={e => onChange(e.target.value)}
      className="touch-target rounded-md border border-navy-300 bg-navy-50 px-3 py-1.5 text-sm text-navy-900 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)] dark:text-[var(--color-text)]"
    />
  </div>
);
