'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const sections = [
  { label: 'Overview', hrefSuffix: '' },
  { label: 'Documents', hrefSuffix: '/documents' },
  { label: 'Votes', hrefSuffix: '/votes' },
  { label: 'Participation', hrefSuffix: '/participation' },
] as const;

export default function BillSectionNav({ billId }: { billId: string }) {
  const pathname = usePathname();
  const baseHref = `/bills/${billId}`;

  return (
    <nav className="mt-6 flex flex-wrap gap-2">
      {sections.map((section) => {
        const href = `${baseHref}${section.hrefSuffix}`;
        const active = pathname === href;

        return (
          <Link
            key={section.label}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              active
                ? 'bg-brand text-white shadow-lg shadow-brand/20'
                : 'border border-slate-200 bg-white text-slate-600 hover:border-brand/20 hover:text-brand-strong'
            }`}
          >
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
