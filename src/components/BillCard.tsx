'use client';

import Link from 'next/link';
import { ArrowUpRight, FileText } from 'lucide-react';
import { Bill, Petition } from '@/types';
import { getBillPdfSourceUrl } from '@/lib/pdf';

interface Props {
  bill: Bill;
  petition?: Petition;
}

export default function BillCard({ bill, petition }: Props) {
  const livePetition = petition ?? bill.petition ?? undefined;
  const progressPercent = livePetition && livePetition.goal > 0 ? (livePetition.signatureCount / livePetition.goal) * 100 : 0;
  const pdfUrl = getBillPdfSourceUrl(bill);
  const introducedAt = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(bill.dateIntroduced));

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-sm transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_40px_-30px_rgba(37,99,235,0.22)]">
      <div className="h-1 bg-gradient-to-r from-brand via-accent to-sky-400" />
      <div className="flex-1 p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-brand-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">
              {bill.category}
            </span>
            {bill.isHot && (
              <span className="rounded-full bg-accent-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-accent">
                Hot
              </span>
            )}
            {pdfUrl && (
              <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-600">
                <FileText size={12} />
                PDF available
              </span>
            )}
          </div>
          <span className="text-xs font-medium uppercase tracking-[0.22em] text-slate-500">{introducedAt}</span>
        </div>

        {bill.sponsor && (
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">
            Sponsored by {bill.sponsor}
          </p>
        )}

        <Link href={`/bills/${bill.id}`} className="mt-4 block">
          <h3 className="text-xl font-semibold leading-snug text-slate-900 transition group-hover:text-brand-strong">
            {bill.title}
          </h3>
        </Link>

        <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-700">{bill.summary}</p>

        {livePetition && (
          <div className="mt-5 rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-3 text-xs font-semibold">
              <span className="uppercase tracking-[0.22em] text-slate-500">Signature goal</span>
              <span className="text-brand-strong">
                {livePetition.signatureCount.toLocaleString()} / {livePetition.goal.toLocaleString()}
              </span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand via-accent to-sky-400"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-slate-100 bg-slate-50/80 p-4">
        <Link
          href={`/bills/${bill.id}`}
          className="inline-flex items-center justify-center rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
        >
          Open bill
        </Link>

        {bill.parliamentUrl ? (
          <a
            href={bill.parliamentUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
          >
            Official page <ArrowUpRight size={14} />
          </a>
        ) : (
          <Link
            href={`/bills/${bill.id}/participation`}
            className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
          >
            Participate
          </Link>
        )}
      </div>
    </article>
  );
}
