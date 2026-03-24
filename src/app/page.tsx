'use client';

import { useDeferredValue, useEffect, useState } from 'react';
import { Activity, MessageSquare, Phone, Search, Users } from 'lucide-react';
import BillCard from '@/components/BillCard';
import BillTimeline from '@/components/BillTimeline';
import MemberTracker from '@/components/MemberTracker';
import ParticipationHub from '@/components/ParticipationHub';
import RegionalImpact from '@/components/RegionalImpact';
import { getDashboard, listBills } from '@/lib/api';
import { Bill, BillCategory, DashboardResponse, TrendingPetition } from '@/types';

const CATEGORY_OPTIONS: Array<'All Categories' | BillCategory> = [
  'All Categories',
  'Finance',
  'Health',
  'Education',
  'Justice',
  'Environment',
];

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

function TrendingSidebar({ items }: { items: TrendingPetition[] }) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm h-full">
      <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">
        <span className="flex h-2 w-2 rounded-full bg-red-500 animate-pulse" />
        Trending Action
      </h3>
      <div className="space-y-6">
        {items.length > 0 ? (
          items.map((item) => {
            const progress = item.goal ? (item.signatures / item.goal) * 100 : item.progressPercent;

            return (
              <div key={item.billId} className="group">
                <div className="flex justify-between items-start mb-1 gap-2">
                  <p className="text-sm font-bold text-slate-800 group-hover:text-indigo-600 transition line-clamp-1">
                    {item.title}
                  </p>
                  <span className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-1 rounded whitespace-nowrap">
                    +{Math.round(progress)}%
                  </span>
                </div>
                <p className="text-xs text-slate-500">{formatNumber(item.signatures)} signatures</p>
                <div className="mt-2 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full" style={{ width: `${Math.min(progress, 100)}%` }} />
                </div>
              </div>
            );
          })
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
            No trending petitions yet. Run the scraper to populate live items.
          </div>
        )}
      </div>
      <button className="w-full mt-8 py-3 text-sm font-bold text-slate-600 bg-slate-50 rounded-xl hover:bg-slate-100 transition">
        View All Petitions
      </button>
    </div>
  );
}

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [bills, setBills] = useState<Bill[]>([]);
  const [billsError, setBillsError] = useState<string | null>(null);
  const [loadedBillsKey, setLoadedBillsKey] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<'All Categories' | BillCategory>('All Categories');
  const deferredSearch = useDeferredValue(search);
  const searchTerm = deferredSearch.trim();
  const currentBillsKey = `search=${searchTerm}|category=${category}`;
  const isDashboardLoading = dashboard === null && dashboardError === null;
  const isBillsLoading = loadedBillsKey !== currentBillsKey;
  const error = dashboardError ?? (loadedBillsKey === currentBillsKey ? billsError : null);
  const hasSearchInput = search.length > 0;

  useEffect(() => {
    let active = true;

    getDashboard()
      .then((data) => {
        if (active) {
          setDashboard(data);
          setDashboardError(null);
        }
      })
      .catch((fetchError) => {
        console.error(fetchError);
        if (active) {
          setDashboardError('We could not load the live dashboard right now.');
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    listBills({
      search: searchTerm || undefined,
      category: category === 'All Categories' ? undefined : category,
      ordering: '-is_hot,-date_introduced',
    })
      .then((payload) => {
        if (active) {
          setBills(payload.results);
          setBillsError(null);
          setLoadedBillsKey(currentBillsKey);
        }
      })
      .catch((fetchError) => {
        console.error(fetchError);
        if (active) {
          setBillsError('We could not load the bill feed right now.');
          setLoadedBillsKey(currentBillsKey);
        }
      });

    return () => {
      active = false;
    };
  }, [currentBillsKey, category, searchTerm]);

  const featuredBill = dashboard?.featuredBill ?? bills[0] ?? null;
  const featuredPetition = featuredBill?.petition ?? null;
  const stats = dashboard?.stats;
  const topCounty = dashboard?.topCounty;
  const isReady = !isDashboardLoading && !isBillsLoading && !error;

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-4xl font-black text-slate-900 tracking-tight">Bunge Mkononi</h1>
            <p className="text-slate-500 mt-2 text-lg font-medium">Tracking Parliament, empowering citizens.</p>
          </div>
          <div className="bg-indigo-600 text-white p-4 rounded-2xl shadow-lg shadow-indigo-200 flex items-center gap-4">
            <div className="bg-white/20 p-3 rounded-xl">
              <Phone size={24} />
            </div>
            <div>
              <p className="text-xs font-bold uppercase opacity-80">Offline Access</p>
              <p className="text-xl font-mono font-bold">*384*16250#</p>
            </div>
          </div>
        </header>

        {error && (
          <div className="mb-8 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {error}
          </div>
        )}

        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          {[
            {
              label: 'Active Bills',
              value: isDashboardLoading ? '...' : formatNumber(stats?.activeBills ?? 0),
              icon: <Activity className="text-blue-500" />,
            },
            {
              label: 'Total Signatures',
              value: isDashboardLoading ? '...' : formatNumber(stats?.totalSignatures ?? 0),
              icon: <Users className="text-emerald-500" />,
            },
            {
              label: 'USSD Sessions',
              value: isDashboardLoading ? '...' : formatNumber(stats?.ussdSessions ?? 0),
              icon: <Phone className="text-orange-500" />,
            },
            {
              label: 'SMS Alerts Sent',
              value: isDashboardLoading ? '...' : formatNumber(stats?.smsAlertsSent ?? 0),
              icon: <MessageSquare className="text-indigo-500" />,
            },
          ].map((stat) => (
            <div key={stat.label} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                {stat.icon}
                <span className="text-xs font-bold text-slate-500 uppercase leading-none">{stat.label}</span>
              </div>
              <div className="text-2xl font-black text-slate-900">{stat.value}</div>
            </div>
          ))}
        </section>

        <section className="mb-12 bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <span className="flex h-2 w-2 rounded-full bg-red-500 animate-ping" />
            <span className="text-xs font-bold text-red-600 uppercase tracking-widest">Live Tracking: Featured Bill</span>
          </div>

          {featuredBill ? (
            <>
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-8">
                <div>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold uppercase tracking-wide">
                      {featuredBill.category}
                    </span>
                    <span className="px-3 py-1 rounded-full bg-rose-100 text-rose-700 text-xs font-bold uppercase tracking-wide">
                      {featuredBill.status}
                    </span>
                    {featuredBill.sponsor && (
                      <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-bold uppercase tracking-wide">
                        Sponsor: {featuredBill.sponsor}
                      </span>
                    )}
                  </div>
                  <h2 className="text-3xl font-black text-slate-900 uppercase">{featuredBill.title}</h2>
                  <p className="mt-2 text-sm text-slate-500">{featuredBill.summary}</p>
                </div>

                {featuredBill.parliamentUrl && (
                  <a
                    href={featuredBill.parliamentUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition"
                  >
                    Open parliament page
                  </a>
                )}
              </div>

              <BillTimeline currentStage={featuredBill.currentStage ?? featuredBill.status} />

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-12">
                <div className="lg:col-span-2">
                  <MemberTracker billId={featuredBill.id} votes={featuredBill.representativeVotes} />
                </div>
                <div>
                  <RegionalImpact counties={featuredBill.countyStats} />
                </div>
              </div>

              <ParticipationHub
                key={featuredBill.id}
                billId={featuredBill.id}
                billTitle={featuredBill.title}
                initialSignatureCount={featuredPetition?.signatureCount ?? featuredBill.petitionSignatureCount ?? 0}
                initialPolling={featuredBill.polling}
              />
            </>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-slate-500">
              {isReady ? 'No featured bill is available yet.' : 'Loading featured bill...'}
            </div>
          )}
        </section>

        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
              <input
                aria-label="Search bills"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                type="text"
                placeholder="Search by title, summary, sponsor, category, status, or ID..."
                className="w-full pl-12 pr-24 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm focus:ring-2 focus:ring-indigo-500 outline-none transition"
              />
              {hasSearchInput && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                >
                  Clear
                </button>
              )}
            </div>
            <p className="mt-2 text-xs font-medium text-slate-500">
              Search across bill titles, summaries, sponsors, categories, statuses, and IDs.
            </p>
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as 'All Categories' | BillCategory)}
            className="px-4 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm font-medium text-slate-600 outline-none"
          >
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <section className="lg:col-span-3">
            <div className="flex items-center justify-between gap-4 mb-6">
              <h2 className="text-2xl font-bold text-slate-800">Legislative Feed</h2>
              <p className="text-sm text-slate-500">
                {isBillsLoading
                  ? 'Refreshing live data...'
                  : searchTerm
                    ? `${bills.length} result(s) for "${searchTerm}"`
                    : `${bills.length} result(s)`}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {bills.map((bill) => (
                <BillCard key={bill.id} bill={bill} petition={bill.petition ?? undefined} />
              ))}

              {!isBillsLoading && bills.length === 0 && (
                <p className="text-slate-500 col-span-full py-10 text-center">
                  {searchTerm
                    ? `No bills matched "${searchTerm}". Try a different title, sponsor, category, status, or ID.`
                    : 'No bills found matching your criteria.'}
                </p>
              )}
            </div>
          </section>

          <aside className="lg:col-span-1 space-y-6">
            <TrendingSidebar items={dashboard?.trendingPetitions ?? []} />
            <div className="p-5 bg-linear-to-br from-indigo-600 to-violet-700 rounded-2xl text-white shadow-lg">
              <p className="text-xs font-bold uppercase opacity-70 mb-1">Top Active County</p>
              <p className="text-xl font-bold">{topCounty?.county ?? 'Loading...'}</p>
              <p className="text-xs mt-2 opacity-80">
                {topCounty ? `${formatNumber(topCounty.engagementCount)} engagements driving the conversation.` : 'County-level engagement will appear here.'}
              </p>
            </div>
          </aside>
        </div>

        <footer className="mt-20 p-8 bg-slate-900 rounded-3xl text-center">
          <h3 className="text-white text-xl font-bold mb-2">Are you a Civil Society Organization?</h3>
          <p className="text-slate-400 mb-6 text-sm">Partner with us to host your petitions and access citizen data analytics.</p>
          <button className="bg-white text-slate-900 px-8 py-3 rounded-xl font-bold hover:bg-slate-100 transition">
            Contact Partner Desk
          </button>
        </footer>
      </div>
    </main>
  );
}
