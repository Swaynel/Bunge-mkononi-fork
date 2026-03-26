import {
  Bill,
  BillDetail,
  BillCategory,
  BillStatus,
  BillVoteSummary,
  BillVotesResponse,
  AdminSmsMetricsResponse,
  CountyStat,
  DashboardResponse,
  PaginatedResponse,
  PollChoice,
  Representative,
  RepresentativeScrapeSummary,
  RepresentativeScrapeTarget,
  ScrapeSummary,
  SubscriptionCadence,
  SubscriptionChannel,
  SubscriptionRecord,
  SubscriptionScope,
  SubscriptionStatus,
  MessageLanguage,
  SystemLog,
} from '@/types';

const DEFAULT_API_BASE_URL =
  process.env.NODE_ENV === 'production'
    ? 'https://bunge-mkononi.onrender.com/api'
    : 'http://127.0.0.1:8000/api';
const ADMIN_BASIC_AUTH_STORAGE_KEY = 'bunge_admin_basic_auth';
const ADMIN_USERNAME_STORAGE_KEY = 'bunge_admin_username';

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, '');
}

function isBrowser() {
  return typeof window !== 'undefined';
}

function getStoredAdminAuthToken() {
  if (!isBrowser()) {
    return null;
  }

  return window.localStorage.getItem(ADMIN_BASIC_AUTH_STORAGE_KEY);
}

export function getStoredAdminUsername() {
  if (!isBrowser()) {
    return null;
  }

  return window.localStorage.getItem(ADMIN_USERNAME_STORAGE_KEY);
}

export function hasStoredAdminCredentials() {
  return Boolean(getStoredAdminAuthToken());
}

export function saveAdminCredentials(username: string, password: string) {
  if (!isBrowser()) {
    return;
  }

  const encoded = window.btoa(`${username}:${password}`);
  window.localStorage.setItem(ADMIN_BASIC_AUTH_STORAGE_KEY, encoded);
  window.localStorage.setItem(ADMIN_USERNAME_STORAGE_KEY, username);
}

export function clearAdminCredentials() {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(ADMIN_BASIC_AUTH_STORAGE_KEY);
  window.localStorage.removeItem(ADMIN_USERNAME_STORAGE_KEY);
}

function buildApiUrl(path: string, query?: QueryParams) {
  const normalizedPath = path.replace(/^\/+/, '');
  const url = new URL(`${getApiBaseUrl()}/${normalizedPath}`);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') {
        continue;
      }
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

function summarizeText(text: string, limit = 240) {
  const collapsed = text.replace(/\s+/g, ' ').trim();
  if (!collapsed) {
    return '';
  }

  if (collapsed.length <= limit) {
    return collapsed;
  }

  return `${collapsed.slice(0, limit - 3)}...`;
}

function headersToObject(headers: HeadersInit | undefined) {
  const normalized = new Headers(headers ?? {});
  normalized.set('Accept', 'application/json');

  const adminAuthToken = getStoredAdminAuthToken();
  if (adminAuthToken && !normalized.has('Authorization')) {
    normalized.set('Authorization', `Basic ${adminAuthToken}`);
  }

  return normalized;
}

async function parseErrorPayload(response: Response) {
  const contentType = (response.headers.get('content-type') || '').toLowerCase();

  if (contentType.includes('json')) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  if (contentType.includes('text/html')) {
    return null;
  }

  try {
    const detail = summarizeText(await response.text());
    return detail ? { detail } : null;
  } catch {
    return null;
  }
}

function extractErrorMessage(response: Response, payload: unknown) {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail.trim();
    }
  }

  return response.statusText || 'Request failed';
}

async function requestJson<T>(path: string, init: RequestInit & { query?: QueryParams } = {}) {
  const { query, headers, cache, ...rest } = init;
  const normalizedHeaders = headersToObject(headers);

  if (rest.body !== undefined && !normalizedHeaders.has('Content-Type')) {
    normalizedHeaders.set('Content-Type', 'application/json');
  }

  const response = await fetch(buildApiUrl(path, query), {
    cache: cache ?? 'no-store',
    credentials: 'include',
    ...rest,
    headers: normalizedHeaders,
  });

  if (!response.ok) {
    const payload = await parseErrorPayload(response);
    const detail = extractErrorMessage(response, payload);
    throw new ApiError(detail || 'Request failed', response.status, payload);
  }

  return (await response.json()) as T;
}

function unwrapPaginated<T>(payload: PaginatedResponse<T> | T[]) {
  return Array.isArray(payload) ? payload : payload.results;
}

export async function getDashboard() {
  return requestJson<DashboardResponse>('/dashboard/');
}

export async function listBills(query: {
  page?: number;
  search?: string;
  category?: BillCategory;
  sponsor?: string;
  from_date?: string;
  to_date?: string;
  ordering?: string;
  status?: BillStatus;
  hot?: boolean;
} = {}) {
  return requestJson<PaginatedResponse<Bill>>('/bills/', {
    query: {
      ...query,
      hot: typeof query.hot === 'boolean' ? (query.hot ? 'true' : 'false') : undefined,
    },
  });
}

export async function getBill(id: string) {
  return requestJson<BillDetail>(`/bills/${id}/`);
}

export async function listRepresentatives(query: { billId?: string; search?: string } = {}) {
  return unwrapPaginated(
    await requestJson<PaginatedResponse<Representative>>('/representatives/', {
      query: {
        billId: query.billId,
        search: query.search,
      },
    }),
  );
}

export async function getBillVotes(billId: string) {
  return requestJson<BillVotesResponse>(`/bills/${billId}/votes/`);
}

export async function getBillVoteSummary(billId: string) {
  return requestJson<BillVoteSummary>(`/bills/${billId}/votes/summary/`);
}

export async function listCountyStats(query: { billId?: string } = {}) {
  return unwrapPaginated(
    await requestJson<PaginatedResponse<CountyStat>>('/counties/', {
      query: {
        bill: query.billId,
      },
    }),
  );
}

export async function listSystemLogs(query: { eventType?: string } = {}) {
  return requestJson<PaginatedResponse<SystemLog>>('/logs/', {
    query: {
      eventType: query.eventType,
    },
  });
}

export async function listScrapeHistory() {
  return requestJson<SystemLog[]>('/scrape/history/');
}

export async function getAdminMetrics() {
  return requestJson<AdminSmsMetricsResponse>('/admin/metrics/');
}

export async function postVote(payload: { billId: string; choice: PollChoice; phoneNumber?: string }) {
  return requestJson<{
    id: number;
    billId: string;
    phoneNumber: string;
    choice: PollChoice;
    createdAt: string;
    petitionSignatureCount: number;
  }>('/votes/', {
    method: 'POST',
    body: JSON.stringify({
      billId: payload.billId,
      phoneNumber: payload.phoneNumber ?? '',
      choice: payload.choice,
    }),
  });
}

export async function createSubscription(payload: {
  billId?: string;
  phoneNumber: string;
  channel?: SubscriptionChannel;
  scope?: SubscriptionScope;
  targetValue?: string;
  language?: MessageLanguage;
  cadence?: SubscriptionCadence;
  status?: SubscriptionStatus;
}) {
  return requestJson<SubscriptionRecord>('/track/', {
    method: 'POST',
    body: JSON.stringify({
      billId: payload.billId,
      phoneNumber: payload.phoneNumber,
      channel: payload.channel,
      scope: payload.scope,
      targetValue: payload.targetValue,
      language: payload.language,
      cadence: payload.cadence,
      status: payload.status,
    }),
  });
}

export async function trackSubscription(payload: { billId?: string; phoneNumber: string; channel?: SubscriptionChannel }) {
  return createSubscription(payload);
}

export async function lookupSubscriptions(phoneNumber: string) {
  return requestJson<{
    phoneNumber: string;
    count: number;
    subscriptions: SubscriptionRecord[];
  }>('/subscriptions/lookup/', {
    method: 'POST',
    body: JSON.stringify({ phoneNumber }),
  });
}

export async function manageSubscription(
  subscriptionId: number,
  payload: {
    phoneNumber: string;
    status?: SubscriptionStatus;
    language?: MessageLanguage;
    cadence?: SubscriptionCadence;
  },
) {
  return requestJson<SubscriptionRecord>(`/subscriptions/${subscriptionId}/manage/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateBill(id: string, payload: Partial<Pick<Bill, 'status' | 'title' | 'summary' | 'category' | 'sponsor' | 'parliamentUrl'>>) {
  return requestJson<Bill>(`/bills/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function broadcastBill(id: string, message?: string) {
  return requestJson<{
    billId: string;
    subscriberCount: number;
    message: string;
    logId: number;
  }>(`/bills/${id}/broadcast/`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export async function runScrape(payload: { url?: string; timeout?: number } = {}) {
  return requestJson<ScrapeSummary>('/scrape/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function runRepresentativeScrape(payload: { role?: RepresentativeScrapeTarget; url?: string; timeout?: number } = {}) {
  return requestJson<RepresentativeScrapeSummary>('/scrape/representatives/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
