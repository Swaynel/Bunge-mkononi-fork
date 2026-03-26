'use client';

import Link from 'next/link';
import { ArrowUpRight, BellRing, ExternalLink, FileText } from 'lucide-react';
import { Bill, BillStatus, Petition } from '@/types';
import { getBillPdfSourceUrl } from '@/lib/pdf';

interface Props {
  bill: Bill;
  petition?: Petition;
}

const STAGES: BillStatus[] = ['First Reading', 'Committee', 'Second Reading', 'Third Reading', 'Presidential Assent'];

const STATUS_STYLES: Record<BillStatus, string> = {
  'First Reading': 'bg-slate-100 text-slate-700',
  Committee: 'bg-amber-50 text-amber-800',
  'Second Reading': 'bg-sky-50 text-sky-800',
  'Third Reading': 'bg-violet-50 text-violet-800',
  'Presidential Assent': 'bg-emerald-50 text-emerald-800',
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

export default function BillCard({ bill, petition }: Props) {
  const livePetition = petition ?? bill.petition ?? undefined;
  const currentStage = bill.currentStage ?? bill.status;
  const currentStageIndex = Math.max(STAGES.indexOf(currentStage), 0);
  const pdfUrl = getBillPdfSourceUrl(bill);
  const billNumber = bill.id.replace(/-/g, ' ').toUpperCase();

  return (
    <article className="group px-6 py-6 transition-colors duration-200 hover:bg-slate-50/80">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_240px_260px] xl:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.18em] text-slate-500">
            <span className="metric-mono">{formatDate(bill.dateIntroduced)}</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline-block" />
            <span className="metric-mono">Bill No. {billNumber}</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline-block" />
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-600">
              {bill.category}
            </span>
          </div>

          <Link href={`/bills/${bill.id}`} className="mt-3 block">
            <h3 className="font-[family:var(--font-site-serif)] text-2xl font-semibold leading-tight text-slate-900 transition group-hover:text-brand-strong">
              {bill.title}
            </h3>
          </Link>

          <p className="mt-3 text-sm leading-7 text-slate-600">
            Sponsored by: <span className="font-medium text-slate-700">{bill.sponsor || 'Government of Kenya'}</span>
          </p>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-700">{bill.summary}</p>

          {livePetition && (
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">
              <span className="metric-mono text-slate-700">{livePetition.signatureCount.toLocaleString()}</span> signatures tracked
            </p>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Status</p>
            <span className={`mt-2 inline-flex rounded-xl px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${STATUS_STYLES[currentStage]}`}>
              {currentStage}
            </span>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">House Progress</p>
            <div className="mt-3 flex items-center gap-2">
              {STAGES.map((stage, index) => {
                const isComplete = index <= currentStageIndex;
                const isCurrent = stage === currentStage;

                return (
                  <div key={stage} className="flex min-w-0 flex-1 items-center gap-2">
                    <span
                      className={`flex h-3 w-3 shrink-0 rounded-full border ${
                        isComplete ? 'border-brand bg-brand' : 'border-slate-300 bg-white'
                      } ${isCurrent ? 'ring-4 ring-brand/10' : ''}`}
                    />
                    {index < STAGES.length - 1 && (
                      <span className={`h-px flex-1 ${index < currentStageIndex ? 'bg-brand' : 'bg-slate-200'}`} />
                    )}
                  </div>
                );
              })}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] uppercase tracking-[0.16em] text-slate-500">
              <span>{STAGES[0]}</span>
              <span className="text-right">{STAGES[STAGES.length - 1]}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4 xl:items-end">
          <Link
            href={`/bills/${bill.id}`}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-brand px-5 text-sm font-semibold text-white transition hover:bg-brand-strong"
          >
            Open Bill Story
            <ArrowUpRight size={14} />
          </Link>

          <div className="flex flex-wrap items-center gap-2 xl:justify-end">
            {pdfUrl && (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
                aria-label={`Open PDF for ${bill.title}`}
                title="Open PDF"
              >
                <FileText size={16} />
              </a>
            )}
            <Link
              href={`/bills/${bill.id}/participation`}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
              aria-label={`Follow ${bill.title}`}
              title="Follow bill"
            >
              <BellRing size={16} />
            </Link>
          </div>

          {bill.parliamentUrl ? (
            <a
              href={bill.parliamentUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-brand-strong"
            >
              View on Parliament.go.ke
              <ExternalLink size={14} />
            </a>
          ) : (
            <span className="text-sm font-medium text-slate-400">Parliament source unavailable</span>
          )}
        </div>
      </div>
    </article>
  );
}
