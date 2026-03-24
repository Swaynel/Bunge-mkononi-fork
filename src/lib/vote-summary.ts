import type { BillStatus, BillVoteBreakdown, BillVotePartyBreakdown, BillVoteSummary, RepresentativeVoteSummary, VoteChoice } from '@/types';

type BuildVoteSummaryInput = {
  billId: string;
  billTitle: string;
  billStatus: BillStatus;
  votes: RepresentativeVoteSummary[];
};

type PartyBreakdownRow = BillVotePartyBreakdown & { label: string };

function incrementBucket(bucket: BillVoteBreakdown | BillVotePartyBreakdown, vote: VoteChoice) {
  if (vote === 'Yes') {
    bucket.yes += 1;
    return;
  }

  if (vote === 'No') {
    bucket.no += 1;
    return;
  }

  bucket.abstain += 1;
}

function sortCountyRows(rows: BillVoteBreakdown[]) {
  return rows.sort((left, right) => right.total - left.total || left.county.localeCompare(right.county));
}

function sortPartyRows(rows: PartyBreakdownRow[]) {
  return rows.sort((left, right) => right.total - left.total || left.label.localeCompare(right.label));
}

export function buildVoteSummaryFromVotes({
  billId,
  billTitle,
  billStatus,
  votes,
}: BuildVoteSummaryInput): BillVoteSummary {
  let yes = 0;
  let no = 0;
  let abstain = 0;

  const byCountyMap = new Map<string, BillVoteBreakdown>();
  const byPartyMap = new Map<string, BillVotePartyBreakdown>();

  for (const vote of votes) {
    if (vote.vote === 'Yes') {
      yes += 1;
    } else if (vote.vote === 'No') {
      no += 1;
    } else {
      abstain += 1;
    }

    const county = vote.representative.county?.trim() || 'Unknown';
    const party = vote.representative.party?.trim() || 'Independent';

    const countyBucket = byCountyMap.get(county) ?? { county, yes: 0, no: 0, abstain: 0, total: 0 };
    incrementBucket(countyBucket, vote.vote);
    countyBucket.total += 1;
    byCountyMap.set(county, countyBucket);

    const partyBucket = byPartyMap.get(party) ?? { yes: 0, no: 0, abstain: 0, total: 0 };
    incrementBucket(partyBucket, vote.vote);
    partyBucket.total += 1;
    byPartyMap.set(party, partyBucket);
  }

  const totalVotes = votes.length;
  const byCounty = sortCountyRows(Array.from(byCountyMap.values()));
  const byPartyRows = sortPartyRows(
    Array.from(byPartyMap.entries()).map(
      ([party, data]): PartyBreakdownRow => ({
        label: party,
        ...data,
      }),
    ),
  );
  const byParty = byPartyRows.reduce<Record<string, BillVotePartyBreakdown>>((accumulator, row) => {
    const { label, ...data } = row;
    accumulator[label] = data;
    return accumulator;
  }, {});

  const toPercent = (value: number) => (totalVotes > 0 ? Number(((value / totalVotes) * 100).toFixed(1)) : 0);

  return {
    billId,
    billTitle,
    billStatus,
    totalVotes,
    yes,
    no,
    abstain,
    yesPercent: toPercent(yes),
    noPercent: toPercent(no),
    abstainPercent: toPercent(abstain),
    byCounty,
    byParty,
  };
}
