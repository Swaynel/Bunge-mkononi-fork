import { Bill } from '@/types';

const PDF_PROXY_ROUTE = '/api/pdf';

function parseUrl(value: string) {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

function isParliamentHost(hostname: string) {
  return hostname === 'parliament.go.ke' || hostname.endsWith('.parliament.go.ke');
}

export function isPdfDocumentUrl(value: string | null | undefined) {
  if (!value) {
    return false;
  }

  const parsed = parseUrl(value);
  if (!parsed || parsed.protocol !== 'https:') {
    return false;
  }

  return /\.pdf(?:$|[?#])/i.test(parsed.pathname);
}

export function isAllowedPdfProxySource(value: string | null | undefined) {
  if (!isPdfDocumentUrl(value)) {
    return false;
  }

  const parsed = parseUrl(value as string);
  return Boolean(parsed && isParliamentHost(parsed.hostname));
}

export function getBillPdfSourceUrl(bill: Pick<Bill, 'documentSourceUrl' | 'fullTextUrl' | 'parliamentUrl'>) {
  return [bill.documentSourceUrl, bill.fullTextUrl, bill.parliamentUrl].find((url) => isAllowedPdfProxySource(url)) ?? null;
}

export function buildPdfProxyUrl(sourceUrl: string) {
  const params = new URLSearchParams({ url: sourceUrl });
  return `${PDF_PROXY_ROUTE}?${params.toString()}`;
}

export function getPdfFilename(sourceUrl: string) {
  const parsed = parseUrl(sourceUrl);
  if (!parsed) {
    return 'bill.pdf';
  }

  const rawName = parsed.pathname.split('/').filter(Boolean).pop() ?? 'bill';
  let decodedName = rawName;

  try {
    decodedName = decodeURIComponent(rawName);
  } catch {
    // Keep the raw path segment if decoding fails.
  }

  const sanitizedName = decodedName
    .replace(/[\r\n"]/g, '')
    .replace(/[^\w.\- ()]+/g, '-')
    .slice(0, 120)
    .trim();

  const fallbackName = sanitizedName || 'bill';
  return fallbackName.toLowerCase().endsWith('.pdf') ? fallbackName : `${fallbackName}.pdf`;
}
