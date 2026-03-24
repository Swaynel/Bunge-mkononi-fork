'use client';

import { useMemo, useState } from 'react';
import { MinusCircle, Search, UserCheck, UserX } from 'lucide-react';
import { RepresentativeVoteSummary } from '@/types';

interface Props {
  billId: string;
  votes?: RepresentativeVoteSummary[];
}

export default function MemberTracker({ billId, votes = [] }: Props) {
  const [query, setQuery] = useState('');
  const totalVotes = votes.length;

  const filteredVotes = useMemo(() => {
    const needle = query.trim().toLowerCase();

    if (!needle) {
      return votes;
    }

    return votes.filter((vote) => {
      const representative = vote.representative;
      return (
        representative.name.toLowerCase().includes(needle) ||
        representative.role.toLowerCase().includes(needle) ||
        representative.constituency.toLowerCase().includes(needle) ||
        representative.county.toLowerCase().includes(needle) ||
        representative.party.toLowerCase().includes(needle)
      );
    });
  }, [query, votes]);

  const renderVote = (vote: RepresentativeVoteSummary['vote']) => {
    if (vote === 'Yes') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">
          <UserCheck size={14} /> YES
        </span>
      );
    }

    if (vote === 'No') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-rose-100 text-rose-700 text-xs font-bold">
          <UserX size={14} /> NO
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">
        <MinusCircle size={14} /> ABSTAIN
      </span>
    );
  };

  return (
    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Legislative Accountability</h2>
          <p className="text-sm text-slate-500">
            Bill ID {billId}. {totalVotes > 0 ? `${totalVotes} representative votes recorded.` : 'No representative votes loaded yet.'}
          </p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            type="text"
            placeholder="Search MP, Senator, county, or party..."
            className="pl-10 pr-4 py-2 bg-slate-50 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-bold">
            <tr>
              <th className="px-6 py-4">Representative</th>
              <th className="px-6 py-4">Role</th>
              <th className="px-6 py-4">Constituency</th>
              <th className="px-6 py-4">Party</th>
              <th className="px-6 py-4 text-center">Vote</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredVotes.map((vote) => {
              const representative = vote.representative;
              return (
                <tr key={vote.id} className="hover:bg-slate-50/50 transition">
                  <td className="px-6 py-4 font-semibold text-slate-800">{representative.name}</td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${
                        representative.role === 'Senator'
                          ? 'bg-amber-100 text-amber-700'
                          : representative.role === 'MP'
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {representative.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-600 text-sm">
                    {representative.constituency}, {representative.county}
                  </td>
                  <td className="px-6 py-4 text-slate-600 text-sm">{representative.party}</td>
                  <td className="px-6 py-4 text-center">{renderVote(vote.vote)}</td>
                </tr>
              );
            })}
            {filteredVotes.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-10 text-center text-slate-500 text-sm">
                  No representative votes match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
