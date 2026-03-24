import Link from 'next/link';
import { ChevronLeft, ExternalLink, FileText } from 'lucide-react';
import BillDocumentReader from '@/components/BillDocumentReader';
import BillVoteSummaryPanel from '@/components/BillVoteSummaryPanel';
import BillTimeline from '@/components/BillTimeline';
import ParticipationHub from '@/components/ParticipationHub';
import MemberTracker from '@/components/MemberTracker';
import RegionalImpact from '@/components/RegionalImpact';
import { buildVoteSummaryFromVotes } from '@/lib/vote-summary';
import { getBill, getBillVoteSummary, getBillVotes } from '@/lib/api';
import { BillDetail } from '@/types';

export default async function BillDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: billId } = await params;

  const billPromise = getBill(billId);
  const billVotesPromise = getBillVotes(billId).catch((fetchError) => {
    console.error(fetchError);
    return null;
  });
  const billVoteSummaryPromise = getBillVoteSummary(billId).catch((fetchError) => {
    console.error(fetchError);
    return null;
  });

  let bill: BillDetail | null = null;
  try {
    bill = await billPromise;
  } catch (fetchError) {
    console.error(fetchError);
  }

  const [billVotesResponse, billVoteSummaryResponse] = await Promise.all([
    billVotesPromise,
    billVoteSummaryPromise,
  ]);

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <nav className="p-4 bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <Link href="/" className="p-2 hover:bg-slate-100 rounded-full transition">
            <ChevronLeft size={20} />
          </Link>
          <span className="font-bold text-slate-900 uppercase tracking-tight">Bill Tracking / ID: {billId}</span>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 pt-8">
        {bill ? (
          <div className="space-y-8">
            <header className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex flex-wrap gap-2 mb-4">
                <span className="px-3 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full uppercase">
                  {bill.category}
                </span>
                <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full uppercase">
                  {bill.status}
                </span>
                {bill.sponsor && (
                  <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded-full uppercase">
                    Sponsor: {bill.sponsor}
                  </span>
                )}
              </div>
              <h1 className="text-3xl font-black text-slate-900 mb-4 uppercase">{bill.title}</h1>
              <p className="text-slate-500 mb-6">{bill.summary}</p>
              <BillTimeline currentStage={bill.currentStage ?? bill.status} />
            </header>

            <BillDocumentReader bill={bill} />

            <BillVoteSummaryPanel
              summary={
                billVoteSummaryResponse ??
                buildVoteSummaryFromVotes({
                  billId: bill.id,
                  billTitle: bill.title,
                  billStatus: bill.currentStage ?? bill.status,
                  votes: billVotesResponse?.votes ?? bill.representativeVotes ?? [],
                })
              }
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-8">
                <ParticipationHub
                  key={bill.id}
                  billId={bill.id}
                  billTitle={bill.title}
                  initialSignatureCount={bill.petition?.signatureCount ?? bill.petitionSignatureCount ?? 0}
                  initialPolling={bill.polling}
                />

                <MemberTracker billId={bill.id} votes={billVotesResponse?.votes ?? bill.representativeVotes} />
              </div>

              <aside className="space-y-6">
                <RegionalImpact counties={bill.countyStats} />

                <div className="bg-slate-900 p-6 rounded-2xl text-white shadow-xl">
                  <h3 className="font-bold mb-4 flex items-center gap-2">
                    <FileText size={18} className="text-indigo-400" /> Official Resources
                  </h3>
                  <p className="text-sm text-slate-400 mb-6">Review the official documents and tracker links for this bill.</p>

                  {bill.fullTextUrl ? (
                    <a
                      href={bill.fullTextUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="w-full py-3 bg-white/10 hover:bg-white/20 border border-white/10 rounded-xl text-sm font-bold transition mb-3 inline-flex items-center justify-center gap-2"
                    >
                      Download or Read Full Text <ExternalLink size={14} />
                    </a>
                  ) : (
                    <button className="w-full py-3 bg-white/10 border border-white/10 rounded-xl text-sm font-bold transition mb-3 opacity-70 cursor-not-allowed">
                      Full text not available yet
                    </button>
                  )}

                  {bill.parliamentUrl ? (
                    <a
                      href={bill.parliamentUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 rounded-xl text-sm font-bold transition inline-flex items-center justify-center gap-2"
                    >
                      Open Parliament Page <ExternalLink size={14} />
                    </a>
                  ) : (
                    <button className="w-full py-3 bg-indigo-600 rounded-xl text-sm font-bold transition opacity-70 cursor-not-allowed">
                      Parliament page unavailable
                    </button>
                  )}
                </div>
              </aside>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-slate-600">
            <h1 className="text-2xl font-black text-slate-900 mb-2">Bill not found</h1>
            <p className="mb-6">We could not load bill <span className="font-mono">{billId}</span> from the Django API.</p>
            <Link href="/" className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 transition">
              Back to dashboard
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
