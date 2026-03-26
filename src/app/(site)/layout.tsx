import type { ReactNode } from 'react';
import SiteHeader from '@/components/site/SiteHeader';

export default function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate min-h-screen overflow-x-clip">
      <div className="pointer-events-none absolute inset-x-0 top-[-12rem] -z-10 h-[24rem] bg-[radial-gradient(circle_at_top,rgba(15,118,110,0.18),transparent_60%)]" />
      <div className="pointer-events-none absolute right-0 top-28 -z-10 h-72 w-72 rounded-full bg-[radial-gradient(circle,rgba(199,111,61,0.18),transparent_68%)] blur-3xl" />
      <SiteHeader />
      <main className="pb-20 pt-[11rem] sm:pt-[9rem] lg:pt-[8rem]">{children}</main>
    </div>
  );
}
