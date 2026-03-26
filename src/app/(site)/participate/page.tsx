import Link from 'next/link';
import { ArrowUpRight, PhoneCall, ShieldCheck, Sparkles, TrendingUp } from 'lucide-react';
import ParticipationHub from '@/components/ParticipationHub';
import RegionalImpact from '@/components/RegionalImpact';
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
          <div className="rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {dashboardError}
          </div>
        </div>
      )}

      <section className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
        <div className="relative overflow-hidden rounded-[2.5rem] border border-white/70 bg-surface/95 p-8 shadow-[0_24px_60px_-36px_rgba(16,33,46,0.28)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(15,118,110,0.08),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(199,111,61,0.12),transparent_26%)]" />
          <div className="relative grid gap-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-end">
            <div className="max-w-2xl">
              <span className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand-soft px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.3em] text-brand-strong">
                <Sparkles size={12} />
                Citizen participation
              </span>
              <h1 className="mt-5 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                Take action from any phone, not just a smartphone.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">
                Vote on active bills, subscribe to updates, and follow the public response through a dedicated
                participation page.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/bills"
                  className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                >
                  Browse bills first
                  <ArrowUpRight size={14} />
                </Link>
                <a
                  href="tel:*384*16250#"
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
                >
                  <PhoneCall size={14} />
                  Start with USSD
                </a>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:w-[340px]">
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">USSD sessions</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">{formatNumber(stats?.ussdSessions ?? 0)}</p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">SMS alerts</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">{formatNumber(stats?.smsAlertsSent ?? 0)}</p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">Active bills</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">{formatNumber(stats?.activeBills ?? 0)}</p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">Total signatures</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">
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
          <div className="rounded-[2rem] border border-slate-200 bg-surface/95 p-6 shadow-sm">
            <p className="text-lg font-semibold text-foreground">No featured bill is available yet.</p>
            <p className="mt-2 text-sm text-slate-500">
              Once the dashboard has a featured bill, this page will show live polling and subscription tools.
            </p>
          </div>
        )}

        <aside className="space-y-6">
          {countyData.length > 0 && <RegionalImpact counties={countyData} />}

          <section className="rounded-[2rem] border border-slate-200 bg-surface/95 p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                <ShieldCheck size={16} />
              </span>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-slate-500">How to participate</p>
                <h3 className="text-lg font-semibold text-foreground">Three quick routes</h3>
              </div>
            </div>
            <div className="mt-5 space-y-4">
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                <p className="text-xs font-bold uppercase tracking-[0.3em] text-slate-500">1. Subscribe</p>
                <p className="mt-2 text-sm text-slate-600">
                  Add your phone number to receive updates when a bill changes.
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                <p className="text-xs font-bold uppercase tracking-[0.3em] text-slate-500">2. Vote</p>
                <p className="mt-2 text-sm text-slate-600">
                  Share support, opposition, or a request for more information.
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
                <p className="text-xs font-bold uppercase tracking-[0.3em] text-slate-500">3. Follow the bill</p>
                <p className="mt-2 text-sm text-slate-600">
                  Each bill gets its own route family for overview, documents, votes, and participation.
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                <TrendingUp size={16} />
              </span>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Trending</p>
                <h3 className="text-lg font-semibold text-foreground">What people are rallying around</h3>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {trendingPetitions.length > 0 ? (
                trendingPetitions.slice(0, 3).map((petition) => {
                  const progress = petition.goal ? (petition.signatures / petition.goal) * 100 : petition.progressPercent;

                  return (
                    <div key={petition.billId} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900">{petition.title}</p>
                        <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                          {Math.round(progress)}%
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-slate-600">{formatNumber(petition.signatures)} signatures</p>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand via-accent to-sky-400"
                          style={{ width: `${Math.min(progress, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  Trending petitions will appear here once live data is available.
                </p>
              )}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
