export type BillStatus =
  | 'First Reading'
  | 'Committee'
  | 'Second Reading'
  | 'Third Reading'
  | 'Presidential Assent';

export type BillCategory = 'Finance' | 'Health' | 'Education' | 'Justice' | 'Environment';
export type PollChoice = 'support' | 'oppose' | 'need_more_info';
export type VoteChoice = 'Yes' | 'No' | 'Abstain';
export type CountySentiment = 'Support' | 'Oppose' | 'Mixed';
export type SubscriptionChannel = 'sms' | 'ussd';
export type RepresentativeRole = 'MP' | 'MCA' | 'Senator';
export type RepresentativeScrapeTarget = 'all' | 'MP' | 'Senator';
export type BillDocumentStatus = 'unavailable' | 'needs_ocr' | 'ready' | 'failed';
export type BillDocumentMethod = 'text' | 'ocr';

export type BillDocumentBlock =
  | {
      type: 'heading';
      text: string;
      level?: number;
    }
  | {
      type: 'paragraph';
      text: string;
    }
  | {
      type: 'list';
      items: string[];
    };

export interface BillDocumentPage {
  pageNumber: number;
  blocks: BillDocumentBlock[];
}

export interface PollTally {
  yes: number;
  no: number;
  undecided: number;
}

export interface Petition {
  id: string;
  billId?: string;
  title: string;
  description: string;
  signatureCount: number;
  goal: number;
  progressPercent?: number;
  createdAt?: string;
}

export interface CountyStat {
  billId: string | null;
  county: string;
  engagementCount: number;
  sentiment: CountySentiment;
}

export interface RepresentativeSummary {
  id: string;
  name: string;
  role: RepresentativeRole;
  constituency: string;
  county: string;
  party: string;
  imageUrl?: string;
}

export interface RepresentativeVoteSummary {
  id: string | number;
  billId: string;
  billTitle: string;
  representative: RepresentativeSummary;
  vote: VoteChoice;
  votedAt?: string;
}

export interface BillVoteBreakdown {
  county: string;
  yes: number;
  no: number;
  abstain: number;
  total: number;
}

export interface BillVotePartyBreakdown {
  yes: number;
  no: number;
  abstain: number;
  total: number;
}

export interface BillVoteSummary {
  billId: string;
  billTitle: string;
  billStatus: BillStatus;
  totalVotes: number;
  yes: number;
  no: number;
  abstain: number;
  yesPercent: number;
  noPercent: number;
  abstainPercent: number;
  byCounty: BillVoteBreakdown[];
  byParty: Record<string, BillVotePartyBreakdown>;
}

export interface BillVotesResponse {
  billId: string;
  billTitle: string;
  totalVotes: number;
  votes: RepresentativeVoteSummary[];
}

export interface Representative extends RepresentativeSummary {
  recentVotes?: {
    billId: string;
    billTitle?: string;
    vote: VoteChoice;
  }[];
}

export interface BillTimelineEntry {
  stage: BillStatus;
  date: string;
  completed: boolean;
}

export interface Bill {
  id: string;
  title: string;
  summary: string;
  status: BillStatus;
  category: BillCategory;
  sponsor?: string;
  parliamentUrl?: string;
  dateIntroduced: string;
  isHot?: boolean;
  fullTextUrl?: string;
  documentStatus?: BillDocumentStatus;
  documentMethod?: BillDocumentMethod | '';
  documentSourceUrl?: string;
  documentText?: string;
  documentPages?: BillDocumentPage[];
  documentError?: string;
  documentPageCount?: number;
  documentWordCount?: number;
  documentProcessedAt?: string | null;
  keyPoints?: string[];
  timeline?: BillTimelineEntry[];
  subscriberCount?: number;
  currentStage?: BillStatus;
  petition?: Petition | null;
  petitionSignatureCount?: number;
  petitionGoal?: number;
  petitionProgressPercent?: number;
  polling?: PollTally;
  representativeVotes?: RepresentativeVoteSummary[];
  countyStats?: CountyStat[];
  createdAt?: string;
  updatedAt?: string;
}

export interface BillDetail extends Bill {
  fullTextUrl: string;
  documentStatus: BillDocumentStatus;
  documentMethod: BillDocumentMethod | '';
  documentSourceUrl: string;
  documentText: string;
  documentPages: BillDocumentPage[];
  documentError: string;
  documentPageCount: number;
  documentWordCount: number;
  documentProcessedAt: string | null;
  keyPoints: string[];
  timeline: BillTimelineEntry[];
  currentStage: BillStatus;
  polling: PollTally;
  representativeVotes: RepresentativeVoteSummary[];
  countyStats: CountyStat[];
}

export interface DashboardStats {
  activeBills: number;
  totalSignatures: number;
  ussdSessions: number;
  smsAlertsSent: number;
}

export interface TrendingPetition {
  billId: string;
  title: string;
  signatures: number;
  goal: number;
  progressPercent: number;
}

export interface DashboardResponse {
  stats: DashboardStats;
  featuredBill: Bill | null;
  trendingPetitions: TrendingPetition[];
  topCounty: CountyStat | null;
}

export interface SystemLog {
  id: number;
  eventType: string;
  message: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ScrapeSummary {
  url: string;
  billsFound: number;
  pagesFetched?: number;
  created: number;
  updated: number;
  errors: string[];
  processedBills: ScrapeProcessedBill[];
}

export interface ScrapeProcessedBill {
  billId: string;
  title: string;
  action: 'created' | 'updated';
  sponsor?: string;
}

export interface RepresentativeScrapeProcessedMember {
  id: string | number;
  name: string;
  action: 'created' | 'updated';
}

export interface RepresentativeScrapeRoleSummary {
  role: Exclude<RepresentativeScrapeTarget, 'all'>;
  url: string;
  membersFound: number;
  pagesFetched: number;
  created: number;
  updated: number;
  processed: RepresentativeScrapeProcessedMember[];
  errors: string[];
}

export interface RepresentativeScrapeAllSummary {
  role: 'all';
  membersFound: {
    MP: number;
    Senator: number;
  };
  created: {
    MP: number;
    Senator: number;
  };
  updated: {
    MP: number;
    Senator: number;
  };
  pagesFetched: {
    MP: number;
    Senator: number;
  };
  errors: string[];
}

export type RepresentativeScrapeSummary = RepresentativeScrapeAllSummary | RepresentativeScrapeRoleSummary;

export interface SmsWebhookCallbackUrls {
  ussd: string;
  smsInbound: string;
  smsDeliveryReports: string;
}

export interface AdminSubscriptionMetric {
  id: number;
  billId: string | null;
  billTitle: string | null;
  phoneNumber: string;
  channel: SubscriptionChannel;
  createdAt: string;
}

export interface AdminInboundSmsMetric {
  id: number;
  phoneNumber: string;
  rawPhoneNumber: string;
  message: string;
  messageId: string;
  linkId: string;
  action: string;
  billId: string | null;
  billTitle: string | null;
  created: boolean;
  createdAt: string;
}

export interface AdminDeliveryReportMetric {
  id: number;
  messageId: string;
  phoneNumber: string;
  rawPhoneNumber: string;
  status: string;
  cost: string;
  network: string;
  billId: string | null;
  billTitle: string | null;
  createdAt: string;
}

export interface AdminSmsMetricsResponse {
  callbackUrls: SmsWebhookCallbackUrls;
  subscriptionMetrics: {
    total: number;
    sms: number;
    ussd: number;
    recent: AdminSubscriptionMetric[];
    topBills: Array<{
      billId: string;
      title: string;
      subscriberCount: number;
    }>;
  };
  inboundSms: {
    received: number;
    matchedSubscriptions: number;
    unmatched: number;
    recent: AdminInboundSmsMetric[];
  };
  deliveryReports: {
    received: number;
    delivered: number;
    failed: number;
    pending: number;
    recent: AdminDeliveryReportMetric[];
  };
  broadcastsSent: number;
  inboundTotal: number;
  deliveryTotal: number;
}

export interface ApiErrorPayload {
  detail?: string;
  [key: string]: unknown;
}
