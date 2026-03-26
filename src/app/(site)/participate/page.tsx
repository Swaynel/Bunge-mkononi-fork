import Link from 'next/link';
import { ArrowUpRight, PhoneCall, ShieldCheck, TrendingUp } from 'lucide-react';
import ParticipationHub from '@/components/ParticipationHub';
import RegionalImpact from '@/components/RegionalImpact';
import SiteBreadcrumbs from '@/components/site/SiteBreadcrumbs';
import SubscriptionWorkbench from '@/components/SubscriptionWorkbench';
import { getDashboard } from '@/lib/api';
import { CountyStat } from '@/types';

export const dynamic = 'force-dynamic';

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

export default async function ParticipatePage() {
  let dashboard = null;
  let dashboardError: string | null = null;

  try {
    dashboard = await getDashboard();
  } catch (fetchError) {
    console.error(fetchError);
    dashboardError = 'We could not load the live participation dashboard right now.';
  }

  const featuredBill = dashboard?.featuredBill;
  const topCounty = dashboard?.topCounty;
  const stats = dashboard?.stats;
  const trendingPetitions = dashboard?.trendingPetitions ?? [];
  const countyData: CountyStat[] = featuredBill?.countyStats?.length
    ? featuredBill.countyStats
    : topCounty
      ? [topCounty]
      : [];

  return (
    <main className="pb-20">
      {dashboardError && (
        <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {dashboardError}
          </div>
        </div>
      )}

      <section className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
        <SiteBreadcrumbs items={[{ href: '/', label: 'Home' }, { label: 'Participate' }]} />
        <div className="surface-card relative overflow-hidden p-8">
          <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(15,23,42,0.02),transparent_40%),radial-gradient(circle_at_top_right,rgba(29,78,216,0.05),transparent_24%)]" />
          <div className="relative grid gap-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-end">
            <div className="max-w-2xl">
              <p className="eyebrow text-brand-strong">Participation Hub</p>
              <h1 className="mt-5 font-[family:var(--font-site-serif)] text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                Take action from any phone, not just a smartphone.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">
                Vote on active bills, subscribe to updates, and follow the public response through a dedicated
                participation page.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/bills"
                  className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                >
                  Browse bills first
                  <ArrowUpRight size={14} />
                </Link>
                <a
                  href="tel:*384*16250#"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
                >
                  <PhoneCall size={14} />
                  Start with USSD
                </a>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:w-85">
              <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
                <p className="eyebrow text-slate-500">USSD Sessions</p>
                <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">{formatNumber(stats?.ussdSessions ?? 0)}</p>
              </div>
              <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
                <p className="eyebrow text-slate-500">SMS Alerts</p>
                <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">{formatNumber(stats?.smsAlertsSent ?? 0)}</p>
              </div>
              <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
                <p className="eyebrow text-slate-500">Active Bills</p>
                <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">{formatNumber(stats?.activeBills ?? 0)}</p>
              </div>
              <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
                <p className="eyebrow text-slate-500">Total Signatures</p>
                <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">
                  {formatNumber(stats?.totalSignatures ?? 0)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-8 grid max-w-7xl gap-6 px-4 sm:px-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        {featuredBill ? (
          <ParticipationHub
            billId={featuredBill.id}
            billTitle={featuredBill.title}
            initialSignatureCount={featuredBill.petition?.signatureCount ?? featuredBill.petitionSignatureCount ?? 0}
            initialPolling={featuredBill.polling}
          />
        ) : (
          <div className="surface-card p-6">
            <p className="text-lg font-semibold text-foreground">No featured bill is available yet.</p>
            <p className="mt-2 text-sm text-slate-500">
              Once the dashboard has a featured bill, this page will show live polling and subscription tools.
            </p>
          </div>
        )}

        <aside className="space-y-6">
          {countyData.length > 0 && <RegionalImpact counties={countyData} />}

          <section className="surface-card p-6">
            <div className="mb-6 flex items-center gap-3 border-b border-slate-200 pb-4">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                <ShieldCheck size={16} />
              </span>
              <div>
                <p className="eyebrow text-slate-500">How To Participate</p>
                <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-900">Three Quick Routes</h3>
              </div>
            </div>
            <div className="mt-5 space-y-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">1. Subscribe</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Add your phone number to receive updates when a bill changes.
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">2. Vote</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Share support, opposition, or a request for more information.
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">3. Follow The Bill</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Each bill gets its own route family for overview, documents, votes, and participation.
                </p>
              </div>
            </div>
          </section>

          <section className="surface-card p-6">
            <div className="mb-6 flex items-center gap-3 border-b border-slate-200 pb-4">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                <TrendingUp size={16} />
              </span>
              <div>
                <p className="eyebrow text-slate-500">Trending</p>
                <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-900">What People Are Rallying Around</h3>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {trendingPetitions.length > 0 ? (
                trendingPetitions.slice(0, 3).map((petition) => {
                  const progress = petition.goal ? (petition.signatures / petition.goal) * 100 : petition.progressPercent;

                  return (
                    <div key={petition.billId} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900">{petition.title}</p>
                        <span className="rounded-xl bg-brand-soft px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                          {Math.round(progress)}%
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-slate-600">{formatNumber(petition.signatures)} signatures</p>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                        <div
                          className="h-full rounded-full bg-brand"
                          style={{ width: `${Math.min(progress, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  Trending petitions will appear here once live data is available.
                </p>
              )}
            </div>
          </section>
        </aside>
      </section>

      <section className="mx-auto mt-8 max-w-7xl px-4 sm:px-6">
        <SubscriptionWorkbench
          featuredBill={featuredBill ? { id: featuredBill.id, title: featuredBill.title } : null}
        />
      </section>
    </main>
  );
}
