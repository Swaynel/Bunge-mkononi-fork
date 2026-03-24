'use client';

import { useState } from 'react';
import BillCard from '@/components/BillCard';
import BillTimeline from '@/components/BillTimeline';
import MemberTracker from '@/components/MemberTracker';
import RegionalImpact from '@/components/RegionalImpact';

import { Bill, Petition } from '@/types';
import { Search, Activity, Users, MessageSquare, Phone } from 'lucide-react';

// Trending Sidebar Component
const TRENDING_PETITIONS = [
  { title: "Reject Finance Bill Clause 4", signatures: 12400, trend: "+12% today" },
  { title: "Support Mental Health Funding", signatures: 8200, trend: "+5% today" },
  { title: "Green Energy Subsidy", signatures: 3100, trend: "+2% today" },
];

function TrendingSidebar() {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm h-full">
      <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">
        <span className="flex h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
        Trending Action
      </h3>
      <div className="space-y-6">
        {TRENDING_PETITIONS.map((item, i) => (
          <div key={i} className="group cursor-pointer">
            <div className="flex justify-between items-start mb-1">
              <p className="text-sm font-bold text-slate-800 group-hover:text-indigo-600 transition line-clamp-1">
                {item.title}
              </p>
              <span className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-1 rounded whitespace-nowrap">
                {item.trend}
              </span>
            </div>
            <p className="text-xs text-slate-500">{item.signatures.toLocaleString()} signatures</p>
            <div className="mt-2 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
              <div className="bg-indigo-500 h-full w-2/3"></div>
            </div>
          </div>
        ))}
      </div>
      <button className="w-full mt-8 py-3 text-sm font-bold text-slate-600 bg-slate-50 rounded-xl hover:bg-slate-100 transition">
        View All Petitions
      </button>
    </div>
  );
}

// Mock Data
const MOCK_BILLS: Bill[] = [
  { id: '1', title: 'The Finance Bill 2026', summary: 'Proposed changes to excise duty on digital services and petroleum.', status: 'Committee', category: 'Finance', dateIntroduced: '2026-03-01', isHot: true },
  { id: '2', title: 'Mental Health Amendment Bill', summary: 'Strengthening county-level access to psychiatric care.', status: 'First Reading', category: 'Health', dateIntroduced: '2026-03-15' },
  { id: '3', title: 'Climate Change Act 2026', summary: 'Framework for carbon credit regulation and forest protection.', status: 'Second Reading', category: 'Justice', dateIntroduced: '2026-03-20' }
];

const MOCK_PETITION: Petition = {
  id: 'p1', billId: '1', title: 'Stop Digital Tax Increase', description: 'Reject clause 4 of the Finance Bill.', signatureCount: 8450, goal: 10000
};

export default function Home() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All Categories');

  const filteredBills = MOCK_BILLS.filter(bill => {
    const matchesSearch = bill.title.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = category === 'All Categories' || bill.category === category;
    return matchesSearch && matchesCategory;
  });

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="max-w-6xl mx-auto">
        
        {/* HEADER */}
        <header className="mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-4xl font-black text-slate-900 tracking-tight">Bunge Mkononi</h1>
            <p className="text-slate-500 mt-2 text-lg font-medium">Tracking Parliament, empowering citizens.</p>
          </div>
          
          <div className="bg-indigo-600 text-white p-4 rounded-2xl shadow-lg shadow-indigo-200 flex items-center gap-4">
            <div className="bg-white/20 p-3 rounded-xl">
              <Phone size={24} />
            </div>
            <div>
              <p className="text-xs font-bold uppercase opacity-80">Offline Access</p>
              <p className="text-xl font-mono font-bold">*384*100#</p>
            </div>
          </div>
        </header>

        {/* GLOBAL STATS */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          {[
            { label: 'Active Bills', value: '24', icon: <Activity className="text-blue-500" /> },
            { label: 'Total Signatures', value: '42.5k', icon: <Users className="text-emerald-500" /> },
            { label: 'USSD Sessions', value: '128k', icon: <Phone className="text-orange-500" /> },
            { label: 'SMS Alerts Sent', value: '890k', icon: <MessageSquare className="text-indigo-500" /> },
          ].map((stat, i) => (
            <div key={i} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                {stat.icon}
                <span className="text-xs font-bold text-slate-500 uppercase leading-none">{stat.label}</span>
              </div>
              <div className="text-2xl font-black text-slate-900">{stat.value}</div>
            </div>
          ))}
        </section>

        {/* FEATURED BILL SECTION */}
        <section className="mb-12 bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
           <div className="flex items-center gap-2 mb-4">
              <span className="flex h-2 w-2 rounded-full bg-red-500 animate-ping"></span>
              <span className="text-xs font-bold text-red-600 uppercase tracking-widest">Live Tracking: Featured Bill</span>
           </div>
           <h2 className="text-3xl font-black text-slate-900 mb-8 uppercase">The Finance Bill 2026</h2>
           
           <BillTimeline currentStage="Committee" />
           
           <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-12">
              <div className="lg:col-span-2">
                 <MemberTracker billId="1" />
              </div>
              <div>
                 <RegionalImpact />
              </div>
              
           </div>
        </section>

        {/* SEARCH & FILTER CONTROLS */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input 
              onChange={(e) => setSearch(e.target.value)}
              type="text" 
              placeholder="Search for a bill..." 
              className="w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm focus:ring-2 focus:ring-indigo-500 outline-none transition"
            />
          </div>
          <select 
            onChange={(e) => setCategory(e.target.value)}
            className="px-4 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm font-medium text-slate-600 outline-none"
          >
            <option>All Categories</option>
            <option>Finance</option>
            <option>Health</option>
            <option>Justice</option>
          </select>
        </div>

        {/* MAIN FEED GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <section className="lg:col-span-3">
            <h2 className="text-2xl font-bold text-slate-800 mb-6">Legislative Feed</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {filteredBills.map(bill => (
                <BillCard 
                  key={bill.id} 
                  bill={bill} 
                  petition={bill.id === '1' ? MOCK_PETITION : undefined} 
                />
              ))}
              {filteredBills.length === 0 && (
                <p className="text-slate-500 col-span-full py-10 text-center">No bills found matching your criteria.</p>
              )}
            </div>
          </section>

          <aside className="lg:col-span-1 space-y-6">
            <TrendingSidebar />
            <div className="p-5 bg-linear-to-br from-indigo-600 to-violet-700 rounded-2xl text-white shadow-lg">
              <p className="text-xs font-bold uppercase opacity-70 mb-1">Top Active County</p>
              <p className="text-xl font-bold">Nairobi City</p>
              <p className="text-xs mt-2 opacity-80">45% of engagement originating here.</p>
            </div>
          </aside>
        </div>

        {/* FOOTER */}
        <footer className="mt-20 p-8 bg-slate-900 rounded-3xl text-center">
          <h3 className="text-white text-xl font-bold mb-2">Are you a Civil Society Organization?</h3>
          <p className="text-slate-400 mb-6 text-sm">Partner with us to host your petitions and access citizen data analytics.</p>
          <button className="bg-white text-slate-900 px-8 py-3 rounded-xl font-bold hover:bg-slate-100 transition">
            Contact Partner Desk
          </button>
        </footer>
      </div>
    </main>
  );
}