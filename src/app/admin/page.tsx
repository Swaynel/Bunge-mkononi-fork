'use client';

import { useState } from 'react';
import { 
  LayoutDashboard, 
  Send, 
  FileEdit, 
  Users, 
  PhoneCall, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';

const INITIAL_BILLS = [
  { id: '1', title: 'The Finance Bill 2026', status: 'Committee', subscribers: 1240 },
  { id: '2', title: 'Mental Health Amendment', status: 'First Reading', subscribers: 850 },
];

export default function AdminPanel() {
  const [bills, setBills] = useState(INITIAL_BILLS);
  const [isSending, setIsSending] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>(["System initialized...", "AT Sandbox Connected."]);

  const triggerSMS = (billId: string, title: string) => {
    setIsSending(billId);
    
    // Simulating Africa's Talking API Call
    setTimeout(() => {
      setLogs(prev => [`SMS Broadcast sent for ${title} to ${bills.find(b => b.id === billId)?.subscribers} users.`, ...prev]);
      setIsSending(null);
      alert(`Africa's Talking API: SMS Alerts dispatched for ${title}`);
    }, 2000);
  };

  const updateStatus = (id: string, newStatus: string) => {
    setBills(prev => prev.map(b => b.id === id ? { ...b, status: newStatus } : b));
    setLogs(prev => [`Status updated for Bill #${id} to ${newStatus}`, ...prev]);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 p-6 space-y-8 hidden md:block">
        <div className="flex items-center gap-2 text-indigo-400 font-black text-xl">
          <LayoutDashboard /> Admin
        </div>
        <nav className="space-y-4">
          <div className="text-xs font-bold text-slate-500 uppercase">Management</div>
          <button className="flex items-center gap-3 text-sm font-bold w-full p-3 bg-indigo-600 rounded-xl">
            <FileEdit size={18} /> Manage Bills
          </button>
          <button className="flex items-center gap-3 text-sm font-bold w-full p-3 text-slate-400 hover:bg-slate-800 rounded-xl transition">
            <Users size={18} /> User Data
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-y-auto">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-2xl font-black">Bunge Mkononi Command Center</h1>
            <p className="text-slate-400 text-sm">Manage legislative data and AT infrastructure.</p>
          </div>
          <div className="flex gap-4">
            <div className="bg-slate-800 px-4 py-2 rounded-lg border border-slate-700">
              <p className="text-[10px] text-slate-500 font-bold uppercase">AT Credit</p>
              <p className="text-emerald-400 font-mono font-bold">KES 4,500.00</p>
            </div>
          </div>
        </header>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <PhoneCall className="text-indigo-400 mb-4" />
            <p className="text-3xl font-black">12.4k</p>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mt-1">USSD Hits (24h)</p>
          </div>
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <Send className="text-emerald-400 mb-4" />
            <p className="text-3xl font-black">89k</p>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mt-1">SMS Dispatched</p>
          </div>
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <CheckCircle2 className="text-orange-400 mb-4" />
            <p className="text-3xl font-black">42</p>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mt-1">Active Petitions</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Bill Management Table */}
          <section className="lg:col-span-2 bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
            <div className="p-6 border-b border-slate-700 font-bold">Live Bill Management</div>
            <table className="w-full text-left">
              <thead className="text-[10px] uppercase text-slate-500 bg-slate-900/50">
                <tr>
                  <th className="p-4">Bill Title</th>
                  <th className="p-4">Current Stage</th>
                  <th className="p-4">Subscribers</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {bills.map(bill => (
                  <tr key={bill.id} className="hover:bg-slate-700/30 transition">
                    <td className="p-4 font-bold text-sm">{bill.title}</td>
                    <td className="p-4 text-xs">
                      <select 
                        className="bg-slate-900 border border-slate-600 rounded px-2 py-1 outline-none"
                        value={bill.status}
                        onChange={(e) => updateStatus(bill.id, e.target.value)}
                      >
                        <option>First Reading</option>
                        <option>Committee</option>
                        <option>Second Reading</option>
                        <option>Assent</option>
                      </select>
                    </td>
                    <td className="p-4 text-sm font-mono">{bill.subscribers}</td>
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => triggerSMS(bill.id, bill.title)}
                        disabled={isSending === bill.id}
                        className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 ml-auto ${
                          isSending === bill.id ? 'bg-slate-600' : 'bg-emerald-600 hover:bg-emerald-500'
                        } transition`}
                      >
                        <Send size={14} /> {isSending === bill.id ? 'Sending...' : 'Broadcast SMS'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Activity Log */}
          <section className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <AlertCircle size={18} className="text-indigo-400" /> System Logs
            </h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {logs.map((log, i) => (
                <div key={i} className="text-[11px] font-mono p-3 bg-slate-900 rounded border border-slate-700 text-slate-300">
                  <span className="text-slate-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                  {log}
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}