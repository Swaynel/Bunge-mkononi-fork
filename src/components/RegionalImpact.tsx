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
    <section className="rounded-[2rem] border border-slate-200 bg-surface/95 p-6 shadow-sm">
      <div className="mb-6 flex items-center gap-3">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-accent-soft text-accent">
          <MapPin size={18} />
        </span>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-slate-500">Regional engagement</p>
          <h3 className="text-lg font-semibold text-foreground">County sentiment</h3>
        </div>
      </div>

      {visibleCounties.length > 0 ? (
        <div className="space-y-5">
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
              <div key={`${county.billId ?? 'global'}-${county.county}`} className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-sm font-semibold text-foreground">{county.county}</span>
                    <span className={`ml-2 rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.25em] ${sentimentClass}`}>
                      {county.sentiment}
                    </span>
                  </div>
                  <span className="text-xs font-medium text-slate-500">{county.engagementCount.toLocaleString()} voices</span>
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
        <p className="text-sm leading-6 text-slate-500">
          County engagement will appear here once citizens start interacting with the bill.
        </p>
      )}
    </section>
  );
}
