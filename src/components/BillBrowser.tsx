'use client';

import Link from 'next/link';
import { useDeferredValue, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  ArrowUpRight,
  BarChart3,
  Flame,
  Landmark,
  MessageSquare,
  PhoneCall,
  Search,
  SlidersHorizontal,
  Users,
} from 'lucide-react';
import BillCard from '@/components/BillCard';
import { getDashboard, listBills } from '@/lib/api';
import { Bill, BillCategory, BillStatus, DashboardResponse, TrendingPetition } from '@/types';

const CATEGORY_OPTIONS: Array<'All Categories' | BillCategory> = [
  'All Categories',
  'Finance',
  'Health',
  'Education',
  'Justice',
  'Environment',
];

const STATUS_OPTIONS: Array<'All Statuses' | BillStatus> = [
  'All Statuses',
  'First Reading',
  'Committee',
  'Second Reading',
  'Third Reading',
  'Presidential Assent',
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
    <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="eyebrow text-slate-500">{label}</span>
        <span className="text-brand">{icon}</span>
      </div>
      <p className="metric-mono text-2xl font-semibold text-foreground">{value}</p>
    </div>
  );
}

function FilterButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border px-3 py-2 text-left text-sm font-semibold transition ${
        active
          ? 'border-brand/25 bg-brand-soft text-brand-strong'
          : 'border-slate-200 bg-white text-slate-600 hover:border-brand/20 hover:text-brand-strong'
      }`}
    >
      {children}
    </button>
  );
}

function TrendingSidebar({ items }: { items: TrendingPetition[] }) {
  return (
    <section className="surface-card p-6">
      <div className="mb-5 flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-warning-soft text-warning">
          <Flame size={16} />
        </span>
        <div>
          <p className="eyebrow text-slate-500">Trending Action</p>
          <h3 className="text-lg font-semibold text-foreground">Citizen momentum</h3>
        </div>
      </div>

      <div className="space-y-4">
        {items.length > 0 ? (
          items.map((item) => {
            const progress = item.goal ? (item.signatures / item.goal) * 100 : item.progressPercent;

            return (
              <div key={item.billId} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold leading-6 text-slate-900">{item.title}</p>
                  <span className="metric-mono rounded-xl bg-brand-soft px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                    {Math.round(progress)}%
                  </span>
                </div>
                <p className="metric-mono mt-2 text-xs text-slate-600">{formatNumber(item.signatures)} signatures</p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${Math.min(progress, 100)}%` }} />
                </div>
              </div>
            );
          })
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
            No trending petitions yet. Run the scraper to populate live items.
          </div>
        )}
      </div>

      <Link
        href="/participate"
        className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
      >
        Explore participation
        <ArrowUpRight size={14} />
      </Link>
    </section>
  );
}

function BillRowSkeleton() {
  return (
    <div className="px-6 py-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_240px_260px]">
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="skeleton-line h-4 w-32" />
            <div className="skeleton-line h-4 w-28" />
            <div className="skeleton-line h-4 w-20" />
          </div>
          <div className="skeleton-line h-9 w-4/5" />
          <div className="skeleton-line h-4 w-2/3" />
          <div className="skeleton-line h-4 w-full" />
          <div className="skeleton-line h-4 w-5/6" />
        </div>
        <div className="space-y-4">
          <div className="skeleton-line h-4 w-16" />
          <div className="skeleton-line h-8 w-32" />
          <div className="skeleton-line h-4 w-28" />
          <div className="skeleton-line h-3 w-full" />
        </div>
        <div className="space-y-3 xl:ml-auto xl:w-full">
          <div className="skeleton-line h-11 w-40" />
          <div className="flex gap-2">
            <div className="skeleton-line h-10 w-10" />
            <div className="skeleton-line h-10 w-10" />
          </div>
          <div className="skeleton-line h-4 w-40" />
        </div>
      </div>
    </div>
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
  const [status, setStatus] = useState<'All Statuses' | BillStatus>('All Statuses');
  const [ministry, setMinistry] = useState('All Ministries');
  const [year, setYear] = useState('All Years');
  const deferredSearch = useDeferredValue(search);
  const searchTerm = deferredSearch.trim();
  const currentBillsKey = `search=${searchTerm}|category=${category}|status=${status}`;
  const isDashboardLoading = dashboard === null && dashboardError === null;
  const isBillsLoading = loadedBillsKey !== currentBillsKey;
  const error = dashboardError ?? (loadedBillsKey === currentBillsKey ? billsError : null);
  const hasSearchInput = search.length > 0;
  const searchInputRef = useRef<HTMLInputElement>(null);

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
      status: status === 'All Statuses' ? undefined : status,
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
  }, [category, currentBillsKey, searchTerm, status]);

  useEffect(() => {
    const handleKeyboardShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyboardShortcut);
    return () => {
      window.removeEventListener('keydown', handleKeyboardShortcut);
    };
  }, []);

  const ministryOptions = useMemo(() => {
    const sponsors = new Set<string>();
    bills.forEach((bill) => {
      const sponsor = bill.sponsor?.trim();
      if (sponsor) {
        sponsors.add(sponsor);
      }
    });

    return ['All Ministries', ...Array.from(sponsors).sort((a, b) => a.localeCompare(b))];
  }, [bills]);

  const yearOptions = useMemo(() => {
    const years = new Set<string>();
    bills.forEach((bill) => {
      const parsed = new Date(bill.dateIntroduced);
      if (!Number.isNaN(parsed.getTime())) {
        years.add(String(parsed.getFullYear()));
      }
    });

    return ['All Years', ...Array.from(years).sort((a, b) => Number(b) - Number(a))];
  }, [bills]);

  const resolvedMinistry = ministryOptions.includes(ministry) ? ministry : 'All Ministries';
  const resolvedYear = yearOptions.includes(year) ? year : 'All Years';

  const filteredBills = useMemo(() => {
    return bills.filter((bill) => {
      const matchesMinistry = resolvedMinistry === 'All Ministries' || (bill.sponsor || 'Government of Kenya') === resolvedMinistry;
      const billYear = String(new Date(bill.dateIntroduced).getFullYear());
      const matchesYear = resolvedYear === 'All Years' || billYear === resolvedYear;
      return matchesMinistry && matchesYear;
    });
  }, [bills, resolvedMinistry, resolvedYear]);

  const featuredBill = dashboard?.featuredBill ?? filteredBills[0] ?? null;
  const stats = dashboard?.stats;
  const topCounty = dashboard?.topCounty;
  const activeResultLabel = searchTerm ? `${filteredBills.length} results for "${searchTerm}"` : `${filteredBills.length} bills`;
  const activeFilterCount = [category !== 'All Categories', status !== 'All Statuses', ministry !== 'All Ministries', year !== 'All Years'].filter(Boolean).length;

  return (
    <main className="pb-20">
      {error && (
        <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {error}
          </div>
        </div>
      )}

      <section className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
        <div className="surface-card relative overflow-hidden p-8">
          <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(15,23,42,0.02),transparent_32%),radial-gradient(circle_at_top_right,rgba(15,23,42,0.04),transparent_24%)]" />
          <div className="relative grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="max-w-3xl">
              <p className="eyebrow text-brand-strong">Legislative Archive</p>
              <h1 className="mt-4 font-[family:var(--font-site-serif)] text-4xl font-semibold leading-tight text-slate-900 sm:text-5xl">
                Browse bills in a calmer, more official reading order.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">
                Filter by category, stage, ministry, and year, then move from a concise archive row into each bill’s
                full story, documents, votes, and participation pages.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/"
                  className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                >
                  Back to overview
                  <ArrowUpRight size={14} />
                </Link>
                <Link
                  href="/participate"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
                >
                  Open participation hub
                  <MessageSquare size={14} />
                </Link>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:w-full">
              <SmallStat
                label="Active Bills"
                value={isDashboardLoading ? '...' : formatNumber(stats?.activeBills ?? 0)}
                icon={<Landmark size={16} />}
              />
              <SmallStat
                label="Total Signatures"
                value={isDashboardLoading ? '...' : formatNumber(stats?.totalSignatures ?? 0)}
                icon={<Users size={16} />}
              />
              <SmallStat
                label="USSD Sessions"
                value={isDashboardLoading ? '...' : formatNumber(stats?.ussdSessions ?? 0)}
                icon={<PhoneCall size={16} />}
              />
              <SmallStat
                label="SMS Alerts"
                value={isDashboardLoading ? '...' : formatNumber(stats?.smsAlertsSent ?? 0)}
                icon={<BarChart3 size={16} />}
              />
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-8 grid max-w-7xl gap-6 px-4 sm:px-6 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
        <aside className="xl:sticky xl:top-24 xl:self-start">
          <section className="surface-card p-6">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-4">
              <div>
                <p className="eyebrow text-slate-500">Global Filters</p>
                <h2 className="text-lg font-semibold text-slate-900">Refine Archive</h2>
              </div>
              <span className="rounded-xl bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-strong">
                {activeFilterCount} active
              </span>
            </div>

            <div className="mt-5 space-y-6">
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Category</p>
                <div className="space-y-2">
                  {CATEGORY_OPTIONS.map((option) => (
                    <FilterButton key={option} active={category === option} onClick={() => setCategory(option)}>
                      {option}
                    </FilterButton>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Status</p>
                <div className="space-y-2">
                  {STATUS_OPTIONS.map((option) => (
                    <FilterButton key={option} active={status === option} onClick={() => setStatus(option)}>
                      {option}
                    </FilterButton>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-3 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500" htmlFor="ministry-filter">
                  Ministry / Sponsor
                </label>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-3">
                  <select
                    id="ministry-filter"
                    value={resolvedMinistry}
                    onChange={(e) => setMinistry(e.target.value)}
                    className="w-full bg-transparent text-sm font-semibold text-slate-700 outline-none"
                  >
                    {ministryOptions.map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-3 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500" htmlFor="year-filter">
                  Year Introduced
                </label>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-3">
                  <select
                    id="year-filter"
                    value={resolvedYear}
                    onChange={(e) => setYear(e.target.value)}
                    className="w-full bg-transparent text-sm font-semibold text-slate-700 outline-none"
                  >
                    {yearOptions.map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  setCategory('All Categories');
                  setStatus('All Statuses');
                  setMinistry('All Ministries');
                  setYear('All Years');
                  setSearch('');
                }}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
              >
                <SlidersHorizontal size={14} />
                Reset filters
              </button>
            </div>
          </section>
        </aside>

        <div className="space-y-6">
          <section className="surface-card overflow-hidden">
            <div className="border-b border-slate-200 px-6 py-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <p className="eyebrow text-slate-500">Bills Register</p>
                  <h2 className="mt-2 font-[family:var(--font-site-serif)] text-3xl font-semibold text-slate-900">Structured Legislative List</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Search by title, summary, sponsor, category, status, or bill ID without losing your place in the archive.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-xl bg-brand-soft px-3 py-1.5 text-xs font-semibold text-brand-strong">
                    {isBillsLoading ? 'Refreshing...' : activeResultLabel}
                  </span>
                  {status !== 'All Statuses' && (
                    <span className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">
                      {status}
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-5 relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  aria-label="Search bills"
                  ref={searchInputRef}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  type="text"
                  placeholder="Search bills, sponsors, topics, or IDs..."
                  className="w-full rounded-xl border border-slate-200 bg-white py-4 pl-12 pr-28 text-sm text-foreground outline-none transition placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
                />
                {hasSearchInput && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="absolute right-4 top-1/2 -translate-y-1/2 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <div className="hidden border-b border-slate-200 bg-slate-50/70 px-6 py-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500 xl:grid xl:grid-cols-[minmax(0,1.7fr)_240px_260px]">
              <span>Bill Record</span>
              <span>Status & Progress</span>
              <span className="text-right">Actions</span>
            </div>

            <div className="divide-y divide-slate-200">
              {isBillsLoading
                ? Array.from({ length: 5 }).map((_, index) => <BillRowSkeleton key={index} />)
                : filteredBills.map((bill) => <BillCard key={bill.id} bill={bill} petition={bill.petition ?? undefined} />)}
            </div>
          </section>

          {!isBillsLoading && filteredBills.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center shadow-sm">
              <p className="text-base font-semibold text-slate-900">
                {searchTerm ? `No bills matched "${searchTerm}".` : 'No bills found matching your current archive filters.'}
              </p>
              <p className="mt-2 text-sm text-slate-600">Try a different title, stage, sponsor, year, or category.</p>
            </div>
          )}
        </div>

        <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
          <TrendingSidebar items={dashboard?.trendingPetitions ?? []} />

          <section className="surface-card p-6">
            <p className="eyebrow text-slate-500">Active County Pulse</p>
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-5">
              <p className="eyebrow text-slate-500">County signal</p>
              {topCounty ? (
                <>
                  <h3 className="mt-2 text-2xl font-semibold text-foreground">{topCounty.county}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    <span className="metric-mono">{formatNumber(topCounty.engagementCount)}</span> voices are shaping the debate in this county.
                  </p>
                  <span className="mt-4 inline-flex rounded-xl border border-brand/15 bg-white px-3 py-1.5 text-xs font-semibold text-brand-strong shadow-sm">
                    {topCounty.sentiment} sentiment
                  </span>
                </>
              ) : (
                <div className="mt-3 space-y-3">
                  <div className="skeleton-line h-7 w-2/3" />
                  <div className="skeleton-line h-4 w-full" />
                  <div className="skeleton-line h-4 w-4/5" />
                  <div className="skeleton-line h-8 w-24" />
                </div>
              )}
            </div>
          </section>

          <section className="surface-card p-6">
            <p className="eyebrow text-slate-500">Featured Bill</p>
            {featuredBill ? (
              <div className="mt-4">
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-xl bg-brand-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                    {featuredBill.category}
                  </span>
                  <span className="rounded-xl bg-accent-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-accent">
                    {featuredBill.status}
                  </span>
                </div>
                <h3 className="mt-4 font-[family:var(--font-site-serif)] text-2xl font-semibold text-foreground">
                  {featuredBill.title}
                </h3>
                <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-600">{featuredBill.summary}</p>
                <div className="mt-4 text-xs uppercase tracking-[0.3em] text-slate-500">
                  Introduced {formatDate(featuredBill.dateIntroduced)}
                </div>
                <div className="mt-5 flex gap-2">
                  <Link
                    href={`/bills/${featuredBill.id}`}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                  >
                    Open Bill Story
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                Featured bill data will appear here once the dashboard loads.
              </div>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}
