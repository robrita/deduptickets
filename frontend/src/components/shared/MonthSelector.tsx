import type React from 'react';

interface MonthSelectorProps {
  value: string;
  onChange: (month: string) => void;
}

export const MonthSelector: React.FC<MonthSelectorProps> = ({ value, onChange }) => (
  <div className="flex items-center gap-2">
    <label htmlFor="global-month" className="text-sm font-medium text-white/80">
      Month:
    </label>
    <input
      type="month"
      id="global-month"
      value={value}
      onChange={e => onChange(e.target.value)}
      className="touch-target rounded-md border border-white/25 bg-white/10 px-3 py-1.5 text-sm text-white focus:border-white/50 focus:ring-1 focus:ring-white/25"
    />
  </div>
);
