/**
 * TrendChart component displays simple bar or line visualization for trends.
 * Uses SVG for lightweight rendering without external chart libraries.
 */

import { useMemo } from 'react';

interface TrendChartProps {
  data: { label: string; value: number; growth?: number }[];
  type?: 'bar' | 'horizontal-bar';
  title?: string;
  valueLabel?: string;
  maxBars?: number;
}

function getBarColor(index: number): string {
  const colors = [
    'bg-blue-500',
    'bg-indigo-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-red-500',
    'bg-orange-500',
    'bg-yellow-500',
    'bg-green-500',
    'bg-teal-500',
    'bg-cyan-500',
  ];
  return colors[index % colors.length];
}

export function TrendChart({
  data,
  type = 'horizontal-bar',
  title,
  valueLabel = 'Count',
  maxBars = 10,
}: TrendChartProps) {
  const chartData = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.value - a.value);
    return sorted.slice(0, maxBars);
  }, [data, maxBars]);

  const maxValue = useMemo(() => {
    return Math.max(...chartData.map(d => d.value), 1);
  }, [chartData]);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        {title && <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>}
        <p className="text-gray-500 text-center py-8">No data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {title && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
      )}

      <div className="p-6">
        {type === 'horizontal-bar' && (
          <div className="space-y-3">
            {chartData.map((item, index) => {
              const widthPercent = (item.value / maxValue) * 100;

              return (
                <div key={item.label} className="flex items-center gap-3">
                  <div className="w-32 text-sm text-gray-600 truncate text-right">{item.label}</div>
                  <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getBarColor(index)} transition-all duration-300`}
                      style={{ width: `${widthPercent}%` }}
                    />
                  </div>
                  <div className="w-16 text-sm font-medium text-gray-900 text-right">
                    {item.value}
                  </div>
                  {item.growth !== undefined && (
                    <div
                      className={`w-16 text-sm text-right ${
                        item.growth > 0
                          ? 'text-red-600'
                          : item.growth < 0
                            ? 'text-green-600'
                            : 'text-gray-500'
                      }`}
                    >
                      {item.growth >= 0 ? '+' : ''}
                      {item.growth.toFixed(1)}%
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {type === 'bar' && (
          <div className="flex items-end justify-around h-48 gap-2">
            {chartData.map((item, index) => {
              const heightPercent = (item.value / maxValue) * 100;

              return (
                <div key={item.label} className="flex flex-col items-center gap-1 flex-1 max-w-16">
                  <span className="text-xs text-gray-600">{item.value}</span>
                  <div
                    className={`w-full ${getBarColor(index)} rounded-t transition-all duration-300`}
                    style={{ height: `${heightPercent}%`, minHeight: '4px' }}
                  />
                  <span className="text-xs text-gray-500 truncate w-full text-center">
                    {item.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-gray-100 text-center text-xs text-gray-400">
          {valueLabel}
        </div>
      </div>
    </div>
  );
}

export default TrendChart;
