import type React from 'react';

interface MonthSelectorProps {
  value: string;
  onChange: (month: string) => void;
}

export const MonthSelector: React.FC<MonthSelectorProps> = ({ value, onChange }) => (
  <div className="flex items-center gap-2">
    <label htmlFor="global-month" className="text-sm font-medium text-gray-600">
      Month:
    </label>
    <input
      type="month"
      id="global-month"
      value={value}
      onChange={e => onChange(e.target.value)}
      className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
    />
  </div>
);
