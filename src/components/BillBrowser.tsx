'use client';

import Link from 'next/link';
import { useDeferredValue, useEffect, useState, type ReactNode } from 'react';
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Flame,
  MessageSquare,
  PhoneCall,
  Search,
  SlidersHorizontal,
  Sparkles,
  Users,
} from 'lucide-react';
import BillCard from '@/components/BillCard';
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

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

function SmallStat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: ReactNode;
}) {
  return (
    <div className="rounded-[1.25rem] border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">{label}</span>
        <span className="text-brand">{icon}</span>
      </div>
      <p className="text-2xl font-semibold text-foreground">{value}</p>
    </div>
  );
}

function TrendingSidebar({ items }: { items: TrendingPetition[] }) {
  return (
    <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <Flame size={16} />
        </span>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Trending action</p>
          <h3 className="text-lg font-semibold text-foreground">What citizens are pushing right now</h3>
        </div>
      </div>

      <div className="space-y-4">
        {items.length > 0 ? (
          items.map((item) => {
            const progress = item.goal ? (item.signatures / item.goal) * 100 : item.progressPercent;

            return (
              <div key={item.billId} className="group rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4 transition hover:border-brand/20">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold leading-5 text-slate-900 transition group-hover:text-brand-strong">
                    {item.title}
                  </p>
                  <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                    {Math.round(progress)}%
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-600">{formatNumber(item.signatures)} signatures</p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-brand via-accent to-sky-400"
                    style={{ width: `${Math.min(progress, 100)}%` }}
                  />
                </div>
              </div>
            );
          })
        ) : (
          <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
            No trending petitions yet. Run the scraper to populate live items.
          </div>
        )}
      </div>

      <Link
        href="/participate"
        className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
      >
        Explore participation
        <ArrowUpRight size={14} />
      </Link>
    </section>
  );
}

export default function BillBrowser() {
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
  const stats = dashboard?.stats;
  const topCounty = dashboard?.topCounty;
  const activeResultLabel = searchTerm ? `${bills.length} results for "${searchTerm}"` : `${bills.length} bills`;

  return (
    <main className="pb-20">
      {error && (
        <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
          <div className="rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {error}
          </div>
        </div>
      )}

      <section className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
        <div className="relative overflow-hidden rounded-[2.5rem] border border-slate-200 bg-white p-8 shadow-[0_24px_60px_-36px_rgba(37,99,235,0.18)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(37,99,235,0.08),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(15,118,110,0.08),transparent_24%)]" />
          <div className="relative grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-brand/15 bg-brand-soft px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.3em] text-brand-strong">
                <Sparkles size={12} />
                Bills Library
              </span>
              <h1 className="mt-5 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                Search the bill feed without losing the story behind each record.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">
                Filter by category, sponsor, or status. Then jump into a bill&apos;s own pages for documents, votes, and
                participation instead of squeezing everything into one crowded view.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/"
                  className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                >
                  Back to overview
                  <ArrowUpRight size={14} />
                </Link>
                <Link
                  href="/participate"
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
                >
                  Open participation hub
                  <MessageSquare size={14} />
                </Link>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:w-[340px]">
              <SmallStat
                label="Active bills"
                value={isDashboardLoading ? '...' : formatNumber(stats?.activeBills ?? 0)}
                icon={<Activity size={16} />}
              />
              <SmallStat
                label="Total signatures"
                value={isDashboardLoading ? '...' : formatNumber(stats?.totalSignatures ?? 0)}
                icon={<Users size={16} />}
              />
              <SmallStat
                label="USSD sessions"
                value={isDashboardLoading ? '...' : formatNumber(stats?.ussdSessions ?? 0)}
                icon={<PhoneCall size={16} />}
              />
              <SmallStat
                label="SMS alerts"
                value={isDashboardLoading ? '...' : formatNumber(stats?.smsAlertsSent ?? 0)}
                icon={<BarChart3 size={16} />}
              />
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-8 grid max-w-7xl gap-6 px-4 sm:px-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="space-y-6">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Browse bills</p>
                <h2 className="mt-2 text-2xl font-semibold text-foreground">Legislative feed</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Search by title, summary, sponsor, category, status, or bill ID.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-brand-soft px-3 py-1.5 text-xs font-semibold text-brand-strong">
                  {isBillsLoading ? 'Refreshing...' : activeResultLabel}
                </span>
                <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">
                  <SlidersHorizontal size={12} />
                  {category}
                </span>
              </div>
            </div>

            <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_240px]">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  aria-label="Search bills"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  type="text"
                  placeholder="Search bills, sponsors, topics, or IDs..."
                  className="w-full rounded-[1.5rem] border border-slate-200 bg-white py-4 pl-12 pr-20 text-sm text-foreground outline-none transition placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
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

              <label className="flex items-center gap-3 rounded-[1.5rem] border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700">
                <SlidersHorizontal size={16} className="text-brand" />
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as 'All Categories' | BillCategory)}
                  className="w-full bg-transparent outline-none"
                >
                  {CATEGORY_OPTIONS.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            {bills.map((bill) => (
              <BillCard key={bill.id} bill={bill} petition={bill.petition ?? undefined} />
            ))}
          </div>

          {!isBillsLoading && bills.length === 0 && (
            <div className="rounded-[2rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center shadow-sm">
              <p className="text-base font-semibold text-slate-900">
                {searchTerm ? `No bills matched "${searchTerm}".` : 'No bills found matching your criteria.'}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Try a different title, sponsor, category, status, or bill ID.
              </p>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <TrendingSidebar items={dashboard?.trendingPetitions ?? []} />

          <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Top active county</p>
            <div className="mt-4 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">County pulse</p>
              <h3 className="mt-2 text-2xl font-semibold text-foreground">{topCounty?.county ?? 'Loading...'}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {topCounty
                  ? `${formatNumber(topCounty.engagementCount)} voices are shaping the debate in this county.`
                  : 'County-level engagement will appear here once live data loads.'}
              </p>
              {topCounty && (
                <span className="mt-4 inline-flex rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-brand-strong shadow-sm">
                  {topCounty.sentiment} sentiment
                </span>
              )}
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Featured bill</p>
            {featuredBill ? (
              <div className="mt-4">
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full bg-brand-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                    {featuredBill.category}
                  </span>
                  <span className="rounded-full bg-accent-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-accent">
                    {featuredBill.status}
                  </span>
                </div>
                <h3 className="mt-4 text-xl font-semibold text-foreground">{featuredBill.title}</h3>
                <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-600">{featuredBill.summary}</p>
                <div className="mt-4 text-xs uppercase tracking-[0.3em] text-slate-500">
                  Introduced {formatDate(featuredBill.dateIntroduced)}
                </div>
                <div className="mt-5 flex gap-2">
                  <Link
                    href={`/bills/${featuredBill.id}`}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                  >
                    Open bill story
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                Featured bill data will appear here once the dashboard loads.
              </div>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}
