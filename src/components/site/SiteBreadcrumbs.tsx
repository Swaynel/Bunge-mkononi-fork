import Link from 'next/link';
import { ChevronRight } from 'lucide-react';

interface BreadcrumbItem {
  href?: string;
  label: string;
}

export default function SiteBreadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex flex-wrap items-center gap-2 text-sm text-slate-500">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <div key={`${item.label}-${index}`} className="flex items-center gap-2">
            {item.href && !isLast ? (
              <Link href={item.href} className="font-medium transition hover:text-brand-strong">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? 'max-w-md truncate text-slate-700' : 'font-medium text-slate-600'}>{item.label}</span>
            )}
            {!isLast && <ChevronRight size={14} />}
          </div>
        );
      })}
    </nav>
  );
}
