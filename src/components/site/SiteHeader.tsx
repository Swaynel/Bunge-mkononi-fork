'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, Command, Landmark, MessageSquare, PhoneCall } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Overview' },
  { href: '/bills', label: 'Bills' },
  { href: '/participate', label: 'Participate' },
  { href: '/admin', label: 'Admin' },
] as const;

function isActiveRoute(pathname: string, href: string) {
  if (href === '/') {
    return pathname === '/';
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
        <div className="surface-card flex flex-col gap-4 bg-white/98 px-4 py-4 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand text-white shadow-sm">
              <Landmark size={20} />
            </span>
            <span>
              <span className="eyebrow block text-slate-500">Bunge Mkononi</span>
              <span className="block text-sm font-semibold text-foreground">Parliament in your pocket</span>
            </span>
          </Link>

          <nav className="flex flex-wrap items-center gap-2">
            {NAV_ITEMS.map((item) => {
              const active = isActiveRoute(pathname, item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                    active
                      ? 'bg-brand text-white shadow-lg shadow-brand/15'
                      : 'border border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-brand-strong'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/bills"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-600 transition hover:border-brand/20 hover:text-brand-strong"
            >
              <Command size={14} />
              <span className="metric-mono text-xs">K</span>
              <span className="hidden sm:inline">Search bills</span>
            </Link>
            <Link
              href="/participate"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
            >
              <MessageSquare size={14} />
              Join in
            </Link>
            <a
              href="tel:*384*16250#"
              className="inline-flex items-center gap-2 rounded-xl bg-brand-strong px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand"
            >
              <PhoneCall size={14} />
              <span className="metric-mono">*384*16250#</span>
              <ArrowUpRight size={14} />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
