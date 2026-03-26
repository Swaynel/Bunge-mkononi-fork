import type { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { ArrowUpRight, FileText } from 'lucide-react';
import BillSectionNav from '@/components/bills/BillSectionNav';
import SiteBreadcrumbs from '@/components/site/SiteBreadcrumbs';
import { ApiError, getBill } from '@/lib/api';

export const dynamic = 'force-dynamic';

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

export default async function BillDetailLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id: billId } = await params;

  let bill = null;

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
    <div className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
      <SiteBreadcrumbs items={[{ href: '/', label: 'Home' }, { href: '/bills', label: 'Bills' }, { label: bill.title }]} />

      <section className="surface-card overflow-hidden p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-4xl">
            <div className="flex flex-wrap gap-2">
              <span className="rounded-xl bg-brand-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-brand-strong">
                {bill.category}
              </span>
              <span className="rounded-xl bg-accent-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-accent">
                {stage}
              </span>
              {bill.sponsor && (
                <span className="rounded-xl bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-600">
                  Sponsor: {bill.sponsor}
                </span>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-500">
              <span>Bill ID {bill.id}</span>
              <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline-block" />
              <span>Introduced {formatDate(bill.dateIntroduced)}</span>
            </div>

            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground lg:text-5xl">{bill.title}</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">{bill.summary}</p>

            <div className="mt-6 flex flex-wrap gap-3">
              {bill.parliamentUrl ? (
                <a
                  href={bill.parliamentUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
                >
                  Official parliament page
                  <ArrowUpRight size={14} />
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-500">
                  Official page unavailable
                </span>
              )}

              {bill.fullTextUrl ? (
                <a
                  href={bill.fullTextUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
                >
                  Read full text
                  <FileText size={14} />
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-500">
                  Full text not published yet
                </span>
              )}

              
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:w-[320px]">
            <div className="surface-panel p-4">
              <p className="eyebrow text-slate-500">Document pages</p>
              <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">{bill.documentPageCount ?? 0}</p>
            </div>
            <div className="surface-panel p-4">
              <p className="eyebrow text-slate-500">Document words</p>
              <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">{bill.documentWordCount ?? 0}</p>
            </div>
            <div className="surface-panel p-4">
              <p className="eyebrow text-slate-500">Subscribers</p>
              <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">{bill.subscriberCount ?? 0}</p>
            </div>
            <div className="surface-panel p-4">
              <p className="eyebrow text-slate-500">Signatures</p>
              <p className="metric-mono mt-2 text-2xl font-semibold text-foreground">
                {bill.petition?.signatureCount ?? bill.petitionSignatureCount ?? 0}
              </p>
            </div>
          </div>
        </div>

        <BillSectionNav billId={bill.id} />
      </section>

      <div className="mt-8 pb-20">{children}</div>
    </div>
  );
}
