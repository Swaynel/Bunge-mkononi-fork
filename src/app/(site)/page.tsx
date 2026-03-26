import Link from 'next/link';
import type { ReactNode } from 'react';
import { ArrowUpRight, BookOpen, MessageSquare, PhoneCall, Sparkles, TrendingUp, Vote, AlertCircle } from 'lucide-react';
import { getDashboard } from '@/lib/api';

export const dynamic = 'force-dynamic';

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

function RouteTile({
  href,
  eyebrow,
  title,
  description,
  icon,
}: {
  href: string;
  eyebrow: string;
  title: string;
  description: string;
  icon: ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group relative flex flex-col justify-between border-2 border-slate-200 bg-white p-6 transition-all duration-300 hover:border-brand-strong hover:bg-brand hover:text-white sm:p-8"
    >
      <div>
        <div className="mb-6 inline-flex h-14 w-14 items-center justify-center bg-slate-100 text-slate-900 transition-colors group-hover:bg-white group-hover:text-brand-strong">
          {icon}
        </div>
        <p className="text-xs font-bold uppercase tracking-widest text-slate-500 group-hover:text-brand-soft">{eyebrow}</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 group-hover:text-white">{title}</h2>
        <p className="mt-4 text-sm leading-relaxed text-slate-600 group-hover:text-brand-soft">{description}</p>
      </div>
      <div className="mt-8 flex items-center gap-2 font-bold text-brand-strong group-hover:text-white">
        Explore <ArrowUpRight size={18} className="transition-transform group-hover:translate-x-1 group-hover:-translate-y-1" />
      </div>
    </Link>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-l-4 border-brand-strong py-2 pl-4">
      <p className="text-3xl font-black tracking-tighter text-slate-900">{value}</p>
      <p className="mt-1 text-xs font-bold uppercase tracking-wider text-slate-500">{label}</p>
    </div>
  );
}

export default async function HomePage() {
  let dashboard = null;
  let dashboardError: string | null = null;

  try {
    dashboard = await getDashboard();
  } catch (fetchError) {
    console.error(fetchError);
    dashboardError = 'Live dashboard is currently unreachable. Showing cached data where possible.';
  }

  const stats = dashboard?.stats;
  const featuredBill = dashboard?.featuredBill;
  const trendingPetitions = dashboard?.trendingPetitions ?? [];
  const topCounty = dashboard?.topCounty;

  return (
    <main className="min-h-screen bg-slate-50 pb-24 selection:bg-brand selection:text-white">
      {dashboardError && (
        <div className="flex items-center gap-3 border-b border-rose-200 bg-rose-100 px-6 py-3 text-sm font-bold text-rose-900">
          <AlertCircle size={16} />
          {dashboardError}
        </div>
      )}

      <header className="border-b border-slate-200 bg-white px-4 py-16 sm:px-8 lg:py-24">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-12 lg:grid-cols-[1fr_400px] lg:gap-20">
            <div className="flex flex-col justify-center">
              <span className="mb-6 inline-flex max-w-fit items-center gap-2 bg-brand-strong px-3 py-1 text-xs font-bold uppercase tracking-widest text-white">
                <Sparkles size={14} /> Parliament in your pocket
              </span>
              <h1 className="text-5xl font-black leading-[1.1] tracking-tighter text-slate-900 sm:text-6xl lg:text-7xl">
                Follow bills, votes, and citizen action. <span className="text-brand-strong">Without the noise.</span>
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
                Bunge Mkononi turns raw parliamentary data into a clear, actionable civic workspace.
                Move seamlessly between bill libraries and live participation.
              </p>

              <div className="mt-10 flex flex-wrap gap-4">
                <Link
                  href="/bills"
                  className="inline-flex h-14 items-center justify-center gap-2 bg-slate-900 px-8 text-sm font-bold text-white transition-colors hover:bg-brand-strong"
                >
                  Open bills library <ArrowUpRight size={18} />
                </Link>
                <Link
                  href="/participate"
                  className="inline-flex h-14 items-center justify-center gap-2 border-2 border-slate-900 bg-transparent px-8 text-sm font-bold text-slate-900 transition-colors hover:bg-slate-100"
                >
                  Join the hub <MessageSquare size={18} />
                </Link>
              </div>
            </div>

            <div className="flex flex-col justify-center border border-slate-200 bg-slate-50 p-8">
              <h3 className="mb-8 border-b-2 border-slate-900 pb-2 text-sm font-bold uppercase tracking-widest text-slate-900">
                Live Platform Pulse
              </h3>
              <div className="grid grid-cols-2 gap-x-6 gap-y-8">
                <HeroStat label="Active Bills" value={formatNumber(stats?.activeBills ?? 0)} />
                <HeroStat label="Signatures" value={formatNumber(stats?.totalSignatures ?? 0)} />
                <HeroStat label="USSD Sessions" value={formatNumber(stats?.ussdSessions ?? 0)} />
                <HeroStat label="SMS Alerts" value={formatNumber(stats?.smsAlertsSent ?? 0)} />
              </div>
            </div>
          </div>
        </div>
      </header>

      <section className="mx-auto mt-16 max-w-7xl px-4 sm:px-8">
        <div className="grid gap-px border border-slate-200 bg-slate-200 md:grid-cols-3">
          <RouteTile
            href="/bills"
            eyebrow="Route 01"
            title="Bills Library"
            description="Search, filter, and compare bills in a calmer workspace built for scanning."
            icon={<BookOpen size={24} />}
          />
          <RouteTile
            href="/participate"
            eyebrow="Route 02"
            title="Participation"
            description="Vote, subscribe, and follow live action through SMS and USSD without friction."
            icon={<Vote size={24} />}
          />
          <RouteTile
            href={featuredBill ? `/bills/${featuredBill.id}` : '/bills'}
            eyebrow="Route 03"
            title="Bill Story"
            description="Read one bill at a time through dedicated pages for overview, documents, and votes."
            icon={<TrendingUp size={24} />}
          />
        </div>
      </section>

      <section className="mx-auto mt-16 max-w-7xl px-4 sm:px-8">
        <div className="grid gap-8 lg:grid-cols-[1fr_400px]">
          <div className="space-y-8">
            <div className="border-2 border-slate-900 bg-white p-8 sm:p-10">
              <div className="mb-6 flex items-center justify-between border-b-2 border-slate-900 pb-4">
                <p className="text-sm font-bold uppercase tracking-widest text-slate-900">Featured Bill</p>
                {featuredBill && (
                  <span className="bg-brand-soft px-3 py-1 text-xs font-bold uppercase tracking-wider text-brand-strong">
                    {featuredBill.status}
                  </span>
                )}
              </div>

              {featuredBill ? (
                <>
                  <p className="text-sm font-bold uppercase text-brand-strong">{featuredBill.category}</p>
                  <h2 className="mt-4 text-3xl font-black leading-tight tracking-tight text-slate-900 md:text-4xl">
                    {featuredBill.title}
                  </h2>
                  <p className="mt-6 text-lg leading-relaxed text-slate-600">{featuredBill.summary}</p>
                  <div className="mt-8 flex flex-col items-start gap-6 border border-slate-200 bg-slate-50 p-6 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-xs font-bold uppercase text-slate-500">Sponsored By</p>
                      <p className="mt-1 font-bold text-slate-900">{featuredBill.sponsor || 'Not listed'}</p>
                    </div>
                    <Link
                      href={`/bills/${featuredBill.id}`}
                      className="inline-flex h-12 items-center gap-2 bg-brand-strong px-6 text-sm font-bold text-white transition-colors hover:bg-slate-900"
                    >
                      Read full bill <ArrowUpRight size={16} />
                    </Link>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center font-medium text-slate-500">
                  Data syncing. Featured bill will appear shortly.
                </div>
              )}
            </div>

            <div className="flex flex-col items-center justify-between gap-6 bg-slate-900 p-8 text-white sm:flex-row">
              <div className="max-w-md">
                <p className="text-xs font-bold uppercase tracking-widest text-brand-soft">Offline Access</p>
                <h2 className="mt-2 text-2xl font-bold">Use a phone, not just a browser.</h2>
                <p className="mt-2 text-sm text-slate-400">
                  Track bills and subscribe to updates through USSD and SMS on any device.
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-4 border border-slate-700 bg-slate-800 p-4">
                <PhoneCall size={24} className="text-brand-soft" />
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Dial Now</p>
                  <p className="font-mono text-xl font-bold text-white">*384*16250#</p>
                </div>
              </div>
            </div>
          </div>

          <aside className="space-y-8">
            <div className="border border-slate-200 bg-white p-6">
              <h3 className="mb-6 border-b-2 border-brand-strong pb-2 text-sm font-bold uppercase tracking-widest text-slate-900">
                Trending Petitions
              </h3>
              <div className="space-y-6">
                {trendingPetitions.length > 0 ? (
                  trendingPetitions.slice(0, 3).map((petition) => {
                    const progress = petition.goal ? (petition.signatures / petition.goal) * 100 : petition.progressPercent;
                    return (
                      <div key={petition.billId} className="group cursor-pointer">
                        <div className="flex items-start justify-between gap-4">
                          <p className="text-sm font-bold leading-snug text-slate-900 transition-colors group-hover:text-brand-strong">
                            {petition.title}
                          </p>
                          <span className="shrink-0 text-xs font-black text-brand-strong">{Math.round(progress)}%</span>
                        </div>
                        <div className="mt-3 h-1 w-full bg-slate-100">
                          <div className="h-full bg-brand-strong" style={{ width: `${Math.min(progress, 100)}%` }} />
                        </div>
                        <p className="mt-2 text-xs font-bold text-slate-500">{formatNumber(petition.signatures)} signatures</p>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-sm text-slate-500">No active petitions at this moment.</p>
                )}
              </div>
            </div>

            <div className="border border-brand-soft bg-brand-soft p-6">
              <p className="text-xs font-bold uppercase tracking-widest text-brand-strong">Top Active County</p>
              <h3 className="mt-2 text-3xl font-black tracking-tight text-slate-900">{topCounty?.county ?? 'Loading...'}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {topCounty
                  ? `${formatNumber(topCounty.engagementCount)} voices are actively shaping the conversation here.`
                  : 'Awaiting county-level telemetry.'}
              </p>
              {topCounty && (
                <div className="mt-4 inline-flex items-center gap-2 border border-brand-strong bg-white px-3 py-1 text-xs font-bold text-brand-strong">
                  Sentiment: {topCounty.sentiment}
                </div>
              )}
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
