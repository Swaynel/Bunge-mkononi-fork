import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowRight, MessageSquare, ShieldCheck } from 'lucide-react';
import { ApiError, getBill } from '@/lib/api';
import ParticipationHub from '@/components/ParticipationHub';
import RegionalImpact from '@/components/RegionalImpact';
import type { BillDetail } from '@/types';

export const dynamic = 'force-dynamic';

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

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
      <ParticipationHub
        billId={bill.id}
        billTitle={bill.title}
        initialSignatureCount={bill.petition?.signatureCount ?? bill.petitionSignatureCount ?? 0}
        initialPolling={bill.polling}
      />

      <aside className="space-y-6">
        <RegionalImpact counties={bill.countyStats} />

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-soft text-brand-strong">
              <ShieldCheck size={16} />
            </span>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">How to participate</p>
              <h3 className="text-lg font-semibold text-foreground">Three quick routes</h3>
            </div>
          </div>
          <div className="mt-5 space-y-4">
            <div className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.3em] text-slate-500">SMS</p>
              <p className="mt-2 text-sm text-slate-600">Send TRACK {bill.id} to follow updates on a basic phone.</p>
            </div>
            <div className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.3em] text-slate-500">USSD</p>
              <p className="mt-2 text-sm text-slate-600">Dial *384*16250# to navigate the live civic menu.</p>
            </div>
            <div className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.3em] text-slate-500">Bill detail</p>
              <p className="mt-2 text-sm text-slate-600">
                Use the section tabs to move between overview, documents, votes, and participation.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Next step</p>
          <h3 className="mt-3 text-2xl font-semibold text-foreground">Keep the conversation moving.</h3>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            After voting or subscribing, return to the overview to read the legislative story again or jump straight to
            the documents page for the full text.
          </p>
          <div className="mt-5 flex flex-col gap-3">
            <Link
              href={`/bills/${bill.id}`}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
            >
              Back to overview
              <ArrowRight size={14} />
            </Link>
            <Link
              href={`/bills/${bill.id}/documents`}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
            >
              Read documents
              <MessageSquare size={14} />
            </Link>
          </div>
        </section>
      </aside>
    </div>
  );
}
