'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, Landmark, MessageSquare, PhoneCall, Sparkles } from 'lucide-react';

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
    <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200 bg-white/85 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-4 rounded-[1.5rem] border border-slate-200 bg-white/95 px-4 py-4 shadow-sm sm:px-5 lg:flex-row lg:items-center lg:justify-between">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand text-white shadow-sm">
              <Landmark size={20} />
            </span>
            <span>
              <span className="block text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                Bunge Mkononi
              </span>
              <span className="block text-sm font-semibold text-foreground">
                Parliament in your pocket
              </span>
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
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                    active
                      ? 'bg-brand text-white shadow-lg shadow-brand/20'
                      : 'border border-transparent text-slate-600 hover:border-brand/20 hover:bg-slate-50 hover:text-brand-strong'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand-soft px-3 py-2 text-xs font-semibold text-brand-strong">
              <Sparkles size={14} />
              Live civic data
            </span>
            <Link
              href="/participate"
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
            >
              <MessageSquare size={14} />
              Join in
            </Link>
            <a
              href="tel:*384*16250#"
              className="inline-flex items-center gap-2 rounded-full bg-brand-strong px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand"
            >
              <PhoneCall size={14} />
              *384*16250#
              <ArrowUpRight size={14} />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
