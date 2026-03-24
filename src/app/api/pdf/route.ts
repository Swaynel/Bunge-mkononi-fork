import { NextRequest } from 'next/server';
import { getPdfFilename, isAllowedPdfProxySource } from '@/lib/pdf';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const FORWARDED_HEADERS = ['content-type', 'content-length', 'accept-ranges', 'content-range', 'etag', 'last-modified', 'cache-control'];
const PDF_USER_AGENT =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

function textResponse(message: string, status: number) {
  return new Response(message, {
    status,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}

export async function GET(request: NextRequest) {
  const source = request.nextUrl.searchParams.get('url');

  if (!source) {
    return textResponse('Missing url parameter.', 400);
  }

  if (!isAllowedPdfProxySource(source)) {
    return textResponse('Unsupported PDF source.', 403);
  }

  const forwardedHeaders = new Headers({
    Accept: 'application/pdf,application/octet-stream;q=0.9,*/*;q=0.1',
    'User-Agent': PDF_USER_AGENT,
  });

  const range = request.headers.get('range');
  if (range) {
    forwardedHeaders.set('Range', range);
  }

  let upstream: Response;
  try {
    upstream = await fetch(source, {
      headers: forwardedHeaders,
      redirect: 'follow',
      cache: 'no-store',
    });
  } catch {
    return textResponse('Unable to load the requested PDF.', 502);
  }

  const finalUrl = upstream.url ? new URL(upstream.url) : null;
  if (finalUrl && !isAllowedPdfProxySource(finalUrl.toString())) {
    return textResponse('The PDF redirected to an unsupported host.', 502);
  }

  const responseHeaders = new Headers();
  for (const headerName of FORWARDED_HEADERS) {
    const value = upstream.headers.get(headerName);
    if (value) {
      responseHeaders.set(headerName, value);
    }
  }

  if (!responseHeaders.has('content-type')) {
    responseHeaders.set('Content-Type', 'application/pdf');
  }
  responseHeaders.set('Content-Disposition', `inline; filename="${getPdfFilename(finalUrl?.toString() || source)}"`);
  responseHeaders.set('X-Content-Type-Options', 'nosniff');
  responseHeaders.set('Referrer-Policy', 'no-referrer');
  if (!responseHeaders.has('cache-control')) {
    responseHeaders.set('Cache-Control', 'public, max-age=3600, stale-while-revalidate=86400');
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
