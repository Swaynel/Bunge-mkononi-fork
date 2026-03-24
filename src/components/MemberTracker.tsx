'use client';
import { useState } from 'react';
import { Search, UserCheck, UserX } from 'lucide-react';
import { Representative } from '@/types';

const MOCK_REPS: Representative[] = [
  { id: 'r1', name: 'Hon. Jane Doe', role: 'MP', constituency: 'Westlands', county: 'Nairobi', party: 'Independent', recentVotes: [{ billId: '1', vote: 'No' }] },
  { id: 'r2', name: 'Hon. John Smith', role: 'MP', constituency: 'Kisauni', county: 'Mombasa', party: 'UDA', recentVotes: [{ billId: '1', vote: 'Yes' }] },
  { id: 'r3', name: 'Hon. Ali Hassan', role: 'MP', constituency: 'Nyali', county: 'Mombasa', party: 'ODM', recentVotes: [{ billId: '1', vote: 'No' }] },
];

export default function MemberTracker({ billId }: { billId: string }) {
  const [query, setQuery] = useState('');

  const filteredReps = MOCK_REPS.filter(rep => 
    rep.name.toLowerCase().includes(query.toLowerCase()) || 
    rep.constituency.toLowerCase().includes(query.toLowerCase())
  );
  return (
    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Legislative Accountability</h2>
          <p className="text-sm text-slate-500">See how your representatives voted on this bill.</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
          <input 
            onChange={(e) => setQuery(e.target.value)}
            type="text" placeholder="Search MP or Constituency..." 
            className="pl-10 pr-4 py-2 bg-slate-50 border rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-bold">
            <tr>
              <th className="px-6 py-4">Representative</th>
              <th className="px-6 py-4">Constituency</th>
              <th className="px-6 py-4">Party</th>
              <th className="px-6 py-4 text-center">Vote</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {MOCK_REPS.map((rep) => {
              const voteRecord = rep.recentVotes.find(v => v.billId === billId);
              return (
                <tr key={rep.id} className="hover:bg-slate-50/50 transition">
                  <td className="px-6 py-4 font-semibold text-slate-800">{rep.name}</td>
                  <td className="px-6 py-4 text-slate-600 text-sm">{rep.constituency}, {rep.county}</td>
                  <td className="px-6 py-4 text-slate-600 text-sm">{rep.party}</td>
                  <td className="px-6 py-4 text-center">
                    {voteRecord?.vote === 'Yes' ? (
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">
                        <UserCheck size={14} /> YES
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-rose-100 text-rose-700 text-xs font-bold">
                        <UserX size={14} /> NO
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}