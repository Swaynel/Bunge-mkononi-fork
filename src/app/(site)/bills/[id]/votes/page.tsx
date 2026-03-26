import { notFound } from 'next/navigation';
import { buildVoteSummaryFromVotes } from '@/lib/vote-summary';
import { ApiError, getBill, getBillVoteSummary, getBillVotes } from '@/lib/api';
import BillVoteSummaryPanel from '@/components/BillVoteSummaryPanel';
import MemberTracker from '@/components/MemberTracker';
import type { BillDetail } from '@/types';

export const dynamic = 'force-dynamic';

export default async function BillVotesPage({ params }: { params: Promise<{ id: string }> }) {
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
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    throw error;
  }

  if (!bill) {
    notFound();
  }

  const [billVotesResponse, billVoteSummaryResponse] = await Promise.all([
    billVotesPromise,
    billVoteSummaryPromise,
  ]);

  return (
    <div className="space-y-6">
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

      <MemberTracker billId={bill.id} votes={billVotesResponse?.votes ?? bill.representativeVotes} />
    </div>
  );
}
