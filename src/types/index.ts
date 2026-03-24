export type BillStatus = 'First Reading' | 'Committee' | 'Second Reading' | 'Third Reading' | 'Presidential Assent';

export interface Bill {
  id: string;
  title: string;
  summary: string;
  status: BillStatus;
  category: 'Finance' | 'Health' | 'Education' | 'Justice';
  dateIntroduced: string;
  isHot?: boolean; 
}

export interface Petition {
  id: string;
  billId: string;
  title: string;
  description: string;
  signatureCount: number;
  goal: number;
}

export interface BillDetail extends Bill {
  fullTextUrl: string;
  keyPoints: string[];
  currentStage: BillStatus;
  timeline: { stage: BillStatus; date: string; completed: boolean }[];
  polling: { yes: number; no: number; undecided: number };
}

export interface Representative {
  id: string;
  name: string;
  role: 'MP' | 'MCA' | 'Senator';
  constituency: string;
  county: string;
  party: string;
  recentVotes: { billId: string; vote: 'Yes' | 'No' | 'Abstain' }[];
  image?: string;
}

export interface RegionalStats {
  county: string;
  engagementCount: number; 
  sentiment: 'Support' | 'Oppose' | 'Mixed';
}