import { notFound } from 'next/navigation';
import { ApiError, getBill } from '@/lib/api';
import { getBillPdfSourceUrl } from '@/lib/pdf';
import BillPdfViewer from '@/components/BillPdfViewer';

export const dynamic = 'force-dynamic';

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export default async function BillDocumentsPage({ params }: { params: Promise<{ id: string }> }) {
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

  const pdfSourceUrl = getBillPdfSourceUrl(bill);
  const summaryText = bill.documentText?.trim().slice(0, 600);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <BillPdfViewer billTitle={bill.title} pdfUrl={pdfSourceUrl} officialUrl={bill.parliamentUrl || bill.fullTextUrl} />

      <aside className="space-y-6">
        <section className="rounded-[2rem] border border-slate-200 bg-surface/95 p-6 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-slate-500">Document snapshot</p>
          <dl className="mt-5 space-y-4 text-sm">
            <div className="flex items-center justify-between gap-4 rounded-[1.25rem] bg-white px-4 py-3">
              <dt className="text-slate-500">Source</dt>
              <dd className="font-semibold text-foreground">{bill.documentMethod || 'Unavailable'}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 rounded-[1.25rem] bg-white px-4 py-3">
              <dt className="text-slate-500">Pages</dt>
              <dd className="font-semibold text-foreground">{bill.documentPageCount}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 rounded-[1.25rem] bg-white px-4 py-3">
              <dt className="text-slate-500">Words</dt>
              <dd className="font-semibold text-foreground">{bill.documentWordCount}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 rounded-[1.25rem] bg-white px-4 py-3">
              <dt className="text-slate-500">Processed</dt>
              <dd className="font-semibold text-foreground">
                {bill.documentProcessedAt ? formatDateTime(bill.documentProcessedAt) : 'Not processed yet'}
              </dd>
            </div>
          </dl>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-surface/95 p-6 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-slate-500">Extracted summary</p>
          {bill.keyPoints.length > 0 ? (
            <div className="mt-5 space-y-3">
              {bill.keyPoints.map((point) => (
                <div key={point} className="rounded-[1.25rem] border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
                  {point}
                </div>
              ))}
            </div>
          ) : summaryText ? (
            <p className="mt-5 rounded-[1.25rem] border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
              {summaryText}
            </p>
          ) : (
            <p className="mt-5 rounded-[1.25rem] border border-dashed border-slate-300 bg-white p-5 text-sm leading-6 text-slate-500">
              No extracted summary is available yet.
            </p>
          )}
        </section>
      </aside>
    </div>
  );
}
