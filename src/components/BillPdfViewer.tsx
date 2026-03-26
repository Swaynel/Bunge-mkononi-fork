import { ExternalLink, FileText } from 'lucide-react';
import { buildPdfProxyUrl } from '@/lib/pdf';

interface BillPdfViewerProps {
  billTitle: string;
  pdfUrl: string | null;
  officialUrl?: string;
}

export default function BillPdfViewer({ billTitle, pdfUrl, officialUrl }: BillPdfViewerProps) {
  const proxyUrl = pdfUrl ? buildPdfProxyUrl(pdfUrl) : null;

  return (
    <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-surface/95 shadow-sm">
      <div className="border-b border-slate-100 p-6 md:p-7">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-bold uppercase tracking-[0.35em] text-brand flex items-center gap-2">
              <FileText size={14} />
              Official PDF
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-foreground">Read the full bill inline</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              The bill document is embedded below so you can read the full text without leaving the page.
            </p>
          </div>

          {proxyUrl && (
            <a
              href={proxyUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
            >
              Open PDF in new tab
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      </div>

      {proxyUrl ? (
        <div className="bg-slate-100 p-3 md:p-4">
          <div className="overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white">
            <iframe
              src={proxyUrl}
              title={`${billTitle} official PDF`}
              className="h-[80vh] min-h-[640px] w-full bg-white"
              loading="lazy"
            />
          </div>
        </div>
      ) : (
        <div className="p-6">
          <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">
            <p className="font-semibold text-foreground">No PDF preview is available for this bill yet.</p>
            <p className="mt-2">
              We could not find a direct PDF URL to embed inline. If the official page exists, you can open it from the
              resources panel{officialUrl ? ' below' : '.'}.
            </p>
            {officialUrl && (
              <a
                href={officialUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong"
              >
                Open official page
                <ExternalLink size={14} />
              </a>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
