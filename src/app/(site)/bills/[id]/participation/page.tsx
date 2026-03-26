import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowRight, BellRing, MessageSquare, ShieldCheck, Smartphone } from 'lucide-react';
import { ApiError, getBill } from '@/lib/api';
import ParticipationHub from '@/components/ParticipationHub';
import RegionalImpact from '@/components/RegionalImpact';
import type { BillDetail } from '@/types';

export const dynamic = 'force-dynamic';

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

export default async function BillParticipationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: billId } = await params;

  let bill: BillDetail | null = null;

  try {
    bill = await getBill(billId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    throw error;
  }

  if (!bill) {
    notFound();
  }

  const stage = bill.currentStage ?? bill.status;

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <aside className="xl:sticky xl:top-24 xl:self-start">
        <section className="surface-card p-6">
          <div className="border-b border-slate-200 pb-4">
            <p className="eyebrow text-slate-500">Participation Desk</p>
            <h2 className="text-lg font-semibold text-slate-900">Channels & Guidance</h2>
          </div>

          <div className="mt-5 space-y-6">
            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Current Record</p>
              <div className="space-y-3">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Bill Status</p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{stage}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Introduced</p>
                  <p className="metric-mono mt-2 text-sm font-semibold text-slate-900">{formatDate(bill.dateIntroduced)}</p>
                </div>
              </div>
            </div>

            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Participation Routes</p>
              <div className="space-y-3">
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start gap-3">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                      <MessageSquare size={16} />
                    </span>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">SMS Follow</p>
                      <p className="metric-mono mt-2 text-sm font-semibold text-slate-900">TRACK {bill.id}</p>
                    </div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start gap-3">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                      <Smartphone size={16} />
                    </span>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">USSD Access</p>
                      <p className="metric-mono mt-2 text-sm font-semibold text-slate-900">*384*16250#</p>
                    </div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start gap-3">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
                      <BellRing size={16} />
                    </span>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Bill Story</p>
                      <p className="mt-2 text-sm leading-6 text-slate-700">
                        Vote here, then return to the full bill story for context, documents, and official progress.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <Link
              href={`/bills/${bill.id}`}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
            >
              Return to overview
              <ArrowRight size={14} />
            </Link>
          </div>
        </section>
      </aside>

      <div className="space-y-6">
        <section className="surface-card p-8">
          <div className="border-b border-slate-200 pb-6">
            <p className="eyebrow text-brand-strong">Civic Participation Register</p>
            <h2 className="mt-2 font-[family:var(--font-site-serif)] text-4xl font-semibold text-slate-900">Public Response</h2>
            <p className="mt-3 max-w-3xl text-lg leading-8 text-slate-600">
              Register support, opposition, or a request for more information in a calmer workflow designed to keep the
              bill record clear and credible.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <span className="rounded-xl bg-brand-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
                {bill.category}
              </span>
              <span className="rounded-xl bg-accent-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-accent">
                {stage}
              </span>
            </div>
          </div>

          <ParticipationHub
            billId={bill.id}
            billTitle={bill.title}
            initialSignatureCount={bill.petition?.signatureCount ?? bill.petitionSignatureCount ?? 0}
            initialPolling={bill.polling}
          />
        </section>
      </div>

      <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
        <RegionalImpact counties={bill.countyStats} />

        <section className="surface-card p-6">
          <div className="mb-6 flex items-center gap-3 border-b border-slate-200 pb-4">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
              <ShieldCheck size={16} />
            </span>
            <div>
              <p className="eyebrow text-slate-500">Participation Standard</p>
              <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-900">How Responses Are Used</h3>
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Support</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">Signals direct public approval and adds to the visible support count.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Oppose</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">Captures public resistance and balances the participation record.</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Need More Info</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">Flags uncertainty and indicates where clearer public education may be needed.</p>
            </div>
          </div>
        </section>

        <section className="surface-card bg-slate-900 p-8 text-white">
          <p className="eyebrow text-brand-soft">Next Step</p>
          <h3 className="mt-3 text-2xl font-semibold leading-none">Keep The Record Connected</h3>
          <p className="mt-4 text-sm leading-7 text-slate-400">
            After recording your response, continue to the overview or documents route to reconnect public sentiment
            with the formal legislative text.
          </p>
          <div className="mt-8 space-y-3">
            <Link
              href={`/bills/${bill.id}`}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand text-xs font-semibold uppercase tracking-[0.24em] transition-colors hover:bg-white hover:text-brand-strong"
            >
              Back To Overview
              <ArrowRight size={16} />
            </Link>
            <Link
              href={`/bills/${bill.id}/documents`}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-white text-xs font-semibold uppercase tracking-[0.24em] transition-colors hover:bg-white hover:text-slate-900"
            >
              Read Documents
              <MessageSquare size={16} />
            </Link>
          </div>
        </section>
      </aside>
    </div>
  );
}
