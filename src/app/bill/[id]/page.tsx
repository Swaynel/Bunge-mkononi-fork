//src/app/bill/[id]/page.tsx
import BillTimeline from '@/components/BillTimeline';
import ParticipationHub from '@/components/ParticipationHub';
import MemberTracker from '@/components/MemberTracker';
import RegionalImpact from '@/components/RegionalImpact';
import { FileText, ChevronLeft } from 'lucide-react';
import Link from 'next/link';

export default function BillDetailPage({ params }: { params: { id: string } }) {
  const billId = params.id;

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Mini Nav */}
      <nav className="p-4 bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <Link href="/" className="p-2 hover:bg-slate-100 rounded-full transition">
            <ChevronLeft size={20} />
          </Link>
          <span className="font-bold text-slate-900 uppercase tracking-tight">Bill Tracking / ID: {billId}</span>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 pt-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content (Tracker + Hub + Votes) */}
          <div className="lg:col-span-2 space-y-8">
            <header className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex gap-2 mb-4">
                <span className="px-3 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full">FINANCE</span>
                <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">HIGH INTEREST</span>
              </div>
              <h1 className="text-3xl font-black text-slate-900 mb-6 uppercase">The Finance Bill 2026</h1>
              <BillTimeline currentStage="Committee" />
            </header>

            <ParticipationHub billId={billId} />
            
            <MemberTracker billId={billId} />
          </div>

          {/* Sidebar (Regional Impact + Resources) */}
          <aside className="space-y-6">
            <RegionalImpact />
            
            <div className="bg-slate-900 p-6 rounded-2xl text-white shadow-xl">
              <h3 className="font-bold mb-4 flex items-center gap-2">
                <FileText size={18} className="text-indigo-400" /> Official Resources
              </h3>
              <p className="text-sm text-slate-400 mb-6">Review the official gazetted documents submitted to parliament.</p>
              <button className="w-full py-3 bg-white/10 hover:bg-white/20 border border-white/10 rounded-xl text-sm font-bold transition mb-3">
                Download PDF (14.2 MB)
              </button>
              <button className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 rounded-xl text-sm font-bold transition">
                Read Hansard Records
              </button>
            </div>
          </aside>

        </div>
      </main>
    </div>
  );
}