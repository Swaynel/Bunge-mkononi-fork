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
    <section className="bg-white p-4 md:p-6 rounded-2xl border border-slate-200 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.3em] text-indigo-600 flex items-center gap-2">
            <FileText size={14} />
            Official PDF
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">Read the full bill inline</h2>
          <p className="mt-1 text-sm text-slate-500">
            The bill document is embedded below so you can read the full text without leaving the page.
          </p>
        </div>

        {proxyUrl && (
          <a
            href={proxyUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition"
          >
            Open PDF in new tab
            <ExternalLink size={14} />
          </a>
        )}
      </div>

      {proxyUrl ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-100">
          <iframe
            src={proxyUrl}
            title={`${billTitle} official PDF`}
            className="h-[80vh] min-h-[640px] w-full bg-white"
            loading="lazy"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
          <p className="font-semibold text-slate-900">No PDF preview is available for this bill yet.</p>
          <p className="mt-2">
            We could not find a direct PDF URL to embed inline. If the official page exists, you can open it from the
            resources panel{officialUrl ? ' below' : '.'}.
          </p>
          {officialUrl && (
            <a
              href={officialUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 transition"
            >
              Open official page
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      )}
    </section>
  );
}
