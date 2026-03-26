'use client';

import { MapPin } from 'lucide-react';
import { CountyStat } from '@/types';

interface Props {
  counties?: CountyStat[];
}

export default function RegionalImpact({ counties = [] }: Props) {
  const visibleCounties = counties.slice(0, 4);
  const maxEngagement = Math.max(...visibleCounties.map((county) => county.engagementCount), 1);

  return (
    <section className="surface-card p-6">
      <div className="mb-6 flex items-center gap-3 border-b border-slate-200 pb-4">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-accent-soft text-accent">
          <MapPin size={18} />
        </span>
        <div>
          <p className="eyebrow text-slate-500">Regional Engagement</p>
          <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-900">County Sentiment</h3>
        </div>
      </div>

      {visibleCounties.length > 0 ? (
        <div className="space-y-4">
          {visibleCounties.map((county) => {
            const sentimentClass =
              county.sentiment === 'Oppose'
                ? 'text-rose-600 bg-rose-50'
                : county.sentiment === 'Support'
                  ? 'text-emerald-600 bg-emerald-50'
                  : 'text-amber-600 bg-amber-50';
            const barClass =
              county.sentiment === 'Oppose'
                ? 'bg-rose-500'
                : county.sentiment === 'Support'
                  ? 'bg-emerald-500'
                  : 'bg-amber-500';

            return (
              <div key={`${county.billId ?? 'global'}-${county.county}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-sm font-semibold text-foreground">{county.county}</span>
                    <span className={`ml-2 rounded-xl px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] ${sentimentClass}`}>
                      {county.sentiment}
                    </span>
                  </div>
                  <span className="metric-mono text-xs font-semibold text-slate-500">{county.engagementCount.toLocaleString()} voices</span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${barClass}`}
                    style={{ width: `${Math.max((county.engagementCount / maxEngagement) * 100, 10)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm leading-7 text-slate-500">
          County engagement will appear here once citizens start interacting with the bill.
        </p>
      )}
    </section>
  );
}
