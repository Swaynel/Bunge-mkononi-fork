import { BarChart3, Vote } from 'lucide-react';
import type { BillVotePartyBreakdown, BillVoteSummary } from '@/types';

interface Props {
  summary: BillVoteSummary;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

function VoteMetricCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'emerald' | 'rose' | 'amber' | 'slate';
}) {
  const tones = {
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    rose: 'bg-rose-50 text-rose-700 border-rose-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    slate: 'bg-slate-50 text-slate-700 border-slate-100',
  } as const;

  return (
    <div className={`rounded-[1.5rem] border p-4 ${tones[tone]}`}>
      <p className="text-[10px] font-black uppercase tracking-[0.35em] opacity-70">{label}</p>
      <p className="mt-2 text-3xl font-semibold leading-none">{value}</p>
    </div>
  );
}

function VoteBreakdownTable({
  title,
  subtitle,
  rows,
}: {
  title: string;
  subtitle: string;
  rows: Array<{
    label: string;
    yes: number;
    no: number;
    abstain: number;
    total: number;
  }>;
}) {
  return (
    <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-foreground">{title}</h3>
        <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      </div>

      {rows.length > 0 ? (
        <div className="max-h-[28rem] overflow-auto rounded-[1.25rem] border border-slate-200">
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 bg-white text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">
              <tr>
                <th className="px-4 py-3">Group</th>
                <th className="px-4 py-3 text-center text-emerald-600">Yes</th>
                <th className="px-4 py-3 text-center text-rose-600">No</th>
                <th className="px-4 py-3 text-center text-amber-600">Abstain</th>
                <th className="px-4 py-3 text-center">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => (
                <tr key={row.label} className="transition hover:bg-slate-50/70">
                  <td className="px-4 py-3 font-semibold text-foreground">{row.label}</td>
                  <td className="px-4 py-3 text-center font-semibold text-emerald-700">{row.yes}</td>
                  <td className="px-4 py-3 text-center font-semibold text-rose-700">{row.no}</td>
                  <td className="px-4 py-3 text-center font-semibold text-amber-700">{row.abstain}</td>
                  <td className="px-4 py-3 text-center font-semibold text-foreground">{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
          No breakdown data is available yet.
        </div>
      )}
    </div>
  );
}

function normalizePartyRows(byParty: Record<string, BillVotePartyBreakdown>) {
  return Object.entries(byParty)
    .map(([party, breakdown]) => ({
      label: party,
      ...breakdown,
    }))
    .sort((left, right) => right.total - left.total || left.label.localeCompare(right.label));
}

export default function BillVoteSummaryPanel({ summary }: Props) {
  const countyRows = [...summary.byCounty].sort((left, right) => right.total - left.total || left.county.localeCompare(right.county));
  const partyRows = normalizePartyRows(summary.byParty);
  const leadingLabel =
    summary.totalVotes === 0
      ? 'No votes recorded yet'
      : summary.yes >= summary.no && summary.yes >= summary.abstain
        ? 'Yes is leading'
        : summary.no >= summary.yes && summary.no >= summary.abstain
          ? 'No is leading'
          : 'Abstain is leading';

  return (
    <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-surface/95 shadow-sm">
      <div className="border-b border-slate-100 p-6 md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-black uppercase tracking-[0.35em] text-brand flex items-center gap-2">
              <BarChart3 size={14} /> Vote summary
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-foreground">Parliamentary vote breakdown</h2>
            <p className="mt-2 text-sm text-slate-500">
              {summary.billTitle} • Bill ID {summary.billId}
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-700">{leadingLabel}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center rounded-full bg-brand-soft px-3 py-1 text-xs font-bold uppercase tracking-[0.25em] text-brand-strong">
              {summary.billStatus}
            </span>
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.25em] text-slate-600">
              {formatNumber(summary.totalVotes)} recorded votes
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-8 p-6 md:p-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <VoteMetricCard label="Yes" value={formatNumber(summary.yes)} tone="emerald" />
          <VoteMetricCard label="No" value={formatNumber(summary.no)} tone="rose" />
          <VoteMetricCard label="Abstain" value={formatNumber(summary.abstain)} tone="amber" />
          <VoteMetricCard label="Total" value={formatNumber(summary.totalVotes)} tone="slate" />
        </div>

        <div className="rounded-[1.75rem] border border-slate-200 bg-slate-50/80 p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="flex items-center gap-2 text-base font-semibold text-foreground">
                <Vote className="text-brand-strong" size={18} /> Vote split
              </h3>
              <p className="text-sm text-slate-500">Share of recorded representative votes on this bill.</p>
            </div>
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
              {summary.totalVotes > 0 ? 'Counts and percentages from the vote scrape endpoint' : 'No votes imported yet'}
            </p>
          </div>

          <div className="mt-5 h-3 overflow-hidden rounded-full bg-white shadow-inner">
            <div className="flex h-full w-full">
              <div className="bg-emerald-500" style={{ width: `${summary.yesPercent}%` }} />
              <div className="bg-rose-500" style={{ width: `${summary.noPercent}%` }} />
              <div className="bg-amber-500" style={{ width: `${summary.abstainPercent}%` }} />
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-3 text-xs font-bold uppercase tracking-[0.25em]">
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">Yes {summary.yesPercent}%</span>
            <span className="rounded-full bg-rose-50 px-3 py-1 text-rose-700">No {summary.noPercent}%</span>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">Abstain {summary.abstainPercent}%</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <VoteBreakdownTable
            title="By county"
            subtitle="See how each county leaned on this bill."
            rows={countyRows.map((row) => ({
              label: row.county,
              yes: row.yes,
              no: row.no,
              abstain: row.abstain,
              total: row.total,
            }))}
          />
          <VoteBreakdownTable title="By party" subtitle="Party alignment across the recorded vote." rows={partyRows} />
        </div>
      </div>
    </section>
  );
}
