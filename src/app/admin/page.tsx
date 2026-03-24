'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  CheckCircle2,
  BarChart3,
  FileEdit,
  KeyRound,
  LayoutDashboard,
  LockKeyhole,
  PhoneCall,
  RefreshCcw,
  Send,
  Sparkles,
  Users,
} from 'lucide-react';
import {
  ApiError,
  broadcastBill,
  clearAdminCredentials,
  getStoredAdminUsername,
  hasStoredAdminCredentials,
  listBills,
  listSystemLogs,
  runScrape,
  saveAdminCredentials,
  updateBill,
} from '@/lib/api';
import { Bill, ScrapeSummary, SystemLog } from '@/types';

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

function describeProcessedBills(processedBills: ScrapeSummary['processedBills']) {
  if (processedBills.length === 0) {
    return 'No bills were processed.';
  }

  return processedBills.map((bill) => `${bill.title} (${bill.action})`).join('; ');
}

function isAuthError(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function getActionErrorMessage(error: unknown, fallback: string) {
  if (isAuthError(error)) {
    return 'Stored admin credentials were rejected. Re-enter them above.';
  }

  if (error instanceof ApiError && error.message) {
    return error.message;
  }

  return fallback;
}

export default function AdminPanel() {
  const [bills, setBills] = useState<Bill[]>([]);
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [billsLoaded, setBillsLoaded] = useState(false);
  const [logsLoaded, setLogsLoaded] = useState(false);
  const [isSending, setIsSending] = useState<string | null>(null);
  const [isScraping, setIsScraping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemNote, setSystemNote] = useState<string | null>(null);
  const [credentialForm, setCredentialForm] = useState({ username: '', password: '' });
  const [adminUsername, setAdminUsername] = useState<string | null>(null);
  const [credentialsLoaded, setCredentialsLoaded] = useState(false);

  const isBillsLoading = !billsLoaded;
  const isLogsLoading = !logsLoaded;
  const canUseProtectedActions = Boolean(adminUsername);
  const connectionStatus = !credentialsLoaded
    ? 'Checking saved credentials...'
    : canUseProtectedActions
      ? `Connected as ${adminUsername}`
      : 'Not connected';

  const refreshBills = async () => {
    const payload = await listBills({ ordering: '-date_introduced' });
    setBills(payload.results);
    setBillsLoaded(true);
  };

  const refreshLogs = async () => {
    if (!hasStoredAdminCredentials()) {
      setLogs([]);
      setLogsLoaded(true);
      return false;
    }

    try {
      const payload = await listSystemLogs();
      setLogs(payload.results);
      setLogsLoaded(true);
      return true;
    } catch (fetchError) {
      console.error(fetchError);
      setLogs([]);
      setLogsLoaded(true);

      if (isAuthError(fetchError)) {
        clearAdminCredentials();
        setAdminUsername(null);
        const message = getActionErrorMessage(fetchError, 'Unable to load system logs right now.');
        setSystemNote(message);
        setError(message);
        return false;
      }

      const message = getActionErrorMessage(fetchError, 'Unable to load system logs right now.');
      setSystemNote(message);
      setError(message);
      return false;
    }
  };

  const hydrateAdminCredentials = () => {
    const storedUsername = getStoredAdminUsername();
    const storedCredentials = hasStoredAdminCredentials();

    setAdminUsername(storedCredentials ? storedUsername : null);
    setCredentialForm((current) => ({
      username: storedUsername ?? current.username,
      password: '',
    }));
    setCredentialsLoaded(true);

    return storedCredentials;
  };

  useEffect(() => {
    let active = true;

    refreshBills().catch((fetchError) => {
      console.error(fetchError);
      if (active) {
        setError('We could not load the live bill table right now.');
        setBillsLoaded(true);
      }
    });

    const hasCredentials = hydrateAdminCredentials();

    if (!hasCredentials) {
      setLogs([]);
      setLogsLoaded(true);
      setSystemNote('Add Django admin credentials above to unlock logs, broadcasts, updates, and live scrapes.');
      return () => {
        active = false;
      };
    }

    setSystemNote('Connected to Django admin. Protected actions are unlocked.');
    refreshLogs().catch((fetchError) => {
      console.error(fetchError);
      if (active) {
        setLogs([]);
        setLogsLoaded(true);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  const stats = useMemo(() => {
    const activeBills = bills.filter((bill) => bill.status !== 'Presidential Assent').length;
    const totalSubscribers = bills.reduce((total, bill) => total + (bill.subscriberCount ?? 0), 0);
    const activePetitions = bills.filter((bill) => Boolean(bill.petition)).length;
    const ussdHits = logs
      .filter((log) => log.eventType === 'ussd_hit')
      .reduce((total, log) => total + Number(log.metadata?.quantity ?? 1), 0);
    const smsDispatched = logs
      .filter((log) => log.eventType === 'sms_broadcast')
      .reduce((total, log) => total + Number(log.metadata?.quantity ?? 1), 0);

    return {
      activeBills,
      totalSubscribers,
      activePetitions,
      ussdHits,
      smsDispatched,
    };
  }, [bills, logs]);

  const handleCredentialsSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const username = credentialForm.username.trim();
    const password = credentialForm.password;

    if (!username || !password) {
      setError('Enter both a Django admin username and password.');
      return;
    }

    saveAdminCredentials(username, password);
    setAdminUsername(username);
    setCredentialsLoaded(true);
    setCredentialForm({ username, password: '' });
    setSystemNote(`Saved credentials locally for ${username}. Loading protected data...`);

    const loaded = await refreshLogs();
    if (loaded) {
      setSystemNote(`Connected to Django admin as ${username}.`);
    }
  };

  const handleClearCredentials = () => {
    clearAdminCredentials();
    setAdminUsername(null);
    setCredentialForm((current) => ({
      username: current.username,
      password: '',
    }));
    setLogs([]);
    setLogsLoaded(true);
    setError(null);
    setSystemNote('Admin credentials cleared. Protected actions are locked again.');
  };

  const triggerSMS = async (billId: string, title: string) => {
    if (!canUseProtectedActions) {
      setError('Add Django admin credentials above before broadcasting SMS updates.');
      return;
    }

    setIsSending(billId);
    setError(null);

    try {
      await broadcastBill(billId);
      setSystemNote(`Broadcast queued for ${title}. Subscribers will get the current bill status.`);
      setLogs((current) => [
        {
          id: Date.now(),
          eventType: 'sms_broadcast',
          message: `Broadcast queued for ${title} with the bill's current status.`,
          metadata: { billId, quantity: 1 },
          createdAt: new Date().toISOString(),
        },
        ...current,
      ]);
    } catch (broadcastError) {
      console.error(broadcastError);
      if (isAuthError(broadcastError)) {
        clearAdminCredentials();
        setAdminUsername(null);
      }
      const message = getActionErrorMessage(broadcastError, 'Broadcast failed. Make sure you are signed into Django admin.');
      setSystemNote(message);
      setError(message);
    } finally {
      setIsSending(null);
    }
  };

  const updateStatus = async (id: string, newStatus: string) => {
    if (!canUseProtectedActions) {
      setError('Add Django admin credentials above before changing bill status.');
      return;
    }

    setError(null);

    try {
      const updated = await updateBill(id, { status: newStatus as Bill['status'] });
      setBills((current) => current.map((bill) => (bill.id === id ? updated : bill)));
      setSystemNote(`Status updated for bill #${id}.`);
      setLogs((current) => [
        {
          id: Date.now(),
          eventType: 'status_change',
          message: `Status updated for Bill #${id} to ${newStatus}.`,
          metadata: { billId: id, toStatus: newStatus },
          createdAt: new Date().toISOString(),
        },
        ...current,
      ]);
    } catch (updateError) {
      console.error(updateError);
      if (isAuthError(updateError)) {
        clearAdminCredentials();
        setAdminUsername(null);
      }
      const message = getActionErrorMessage(updateError, 'Status updates require Django admin authentication.');
      setSystemNote(message);
      setError(message);
    }
  };

  const runLiveScrape = async () => {
    if (!canUseProtectedActions) {
      setError('Add Django admin credentials above before running a live scrape.');
      return;
    }

    setIsScraping(true);
    setError(null);
    setBillsLoaded(false);
    setLogsLoaded(false);

    try {
      const summary = await runScrape();
      const pagesNote = summary.pagesFetched ? ` across ${summary.pagesFetched} page(s)` : '';
      setSystemNote(
        `Scrape finished: ${summary.billsFound} bill(s) processed${pagesNote}. ${describeProcessedBills(summary.processedBills)}`,
      );
      await refreshBills();
      await refreshLogs();
    } catch (scrapeError) {
      console.error(scrapeError);
      if (isAuthError(scrapeError)) {
        clearAdminCredentials();
        setAdminUsername(null);
      }
      const message = getActionErrorMessage(scrapeError, 'Live scraping failed. Check the backend logs for details.');
      setSystemNote(message);
      setError(message);
      setBillsLoaded(true);
      setLogsLoaded(true);
    } finally {
      setIsScraping(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex">
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
          <Link
            href="/admin/metrics"
            className="flex items-center gap-3 text-sm font-bold w-full p-3 text-slate-400 hover:bg-slate-800 rounded-xl transition"
          >
            <BarChart3 size={18} /> SMS Metrics
          </Link>
        </nav>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto">
        <header className="flex flex-col gap-4 lg:flex-row lg:justify-between lg:items-center mb-10">
          <div>
            <h1 className="text-2xl font-black">Bunge Mkononi Command Center</h1>
            <p className="text-slate-400 text-sm">Manage live legislative data, broadcasts, and scrape jobs.</p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={runLiveScrape}
              disabled={isScraping || !canUseProtectedActions}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 transition disabled:opacity-60"
            >
              {isScraping ? <RefreshCcw size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {isScraping ? 'Scraping...' : 'Run Live Scrape'}
            </button>
            <div className="bg-slate-800 px-4 py-2 rounded-lg border border-slate-700">
              <p className="text-[10px] text-slate-500 font-bold uppercase">Connection</p>
              <p className={`font-mono font-bold ${canUseProtectedActions ? 'text-emerald-400' : 'text-amber-400'}`}>
                {connectionStatus}
              </p>
            </div>
            {canUseProtectedActions && (
              <button
                type="button"
                onClick={handleClearCredentials}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-bold text-slate-200 hover:bg-slate-700 transition"
              >
                <LockKeyhole size={16} />
                Sign Out
              </button>
            )}
          </div>
        </header>

        {!canUseProtectedActions && (
          <section className="mb-6 rounded-2xl border border-slate-700 bg-slate-800 p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-indigo-300 font-bold">
                  <KeyRound size={18} />
                  Admin Credentials
                </div>
                <p className="text-sm text-slate-400 max-w-2xl">
                  Save a Django admin or staff account in this browser to unlock system logs, bill updates, SMS broadcasts,
                  and live scrape jobs.
                </p>
              </div>

              <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm">
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Status</div>
                <div className={`mt-1 font-bold ${canUseProtectedActions ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {connectionStatus}
                </div>
              </div>
            </div>

            <form onSubmit={handleCredentialsSubmit} className="mt-5 space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm font-medium text-slate-300">
                  <span className="block text-xs uppercase tracking-widest text-slate-500 font-bold">Username</span>
                  <input
                    type="text"
                    value={credentialForm.username}
                    onChange={(event) =>
                      setCredentialForm((current) => ({
                        ...current,
                        username: event.target.value,
                      }))
                    }
                    placeholder="Django admin username"
                    autoComplete="username"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500"
                  />
                </label>

                <label className="space-y-2 text-sm font-medium text-slate-300">
                  <span className="block text-xs uppercase tracking-widest text-slate-500 font-bold">Password</span>
                  <input
                    type="password"
                    value={credentialForm.password}
                    onChange={(event) =>
                      setCredentialForm((current) => ({
                        ...current,
                        password: event.target.value,
                      }))
                    }
                    placeholder="Django admin password"
                    autoComplete="current-password"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-500"
                  />
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-500 transition"
                >
                  <LockKeyhole size={16} />
                  Save Credentials
                </button>
                <p className="text-xs text-slate-500">
                  Stored locally in this browser and sent as HTTP Basic Auth only when the frontend calls Django.
                </p>
              </div>
            </form>
          </section>
        )}

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {systemNote && (
          <div className="mb-6 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            {systemNote}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <PhoneCall className="text-indigo-400 mb-4" />
            <p className="text-3xl font-black">{isBillsLoading ? '...' : formatNumber(stats.ussdHits)}</p>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mt-1">USSD Hits (24h)</p>
          </div>
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <Send className="text-emerald-400 mb-4" />
            <p className="text-3xl font-black">{isLogsLoading ? '...' : formatNumber(stats.smsDispatched)}</p>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mt-1">SMS Dispatched</p>
          </div>
          <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
            <CheckCircle2 className="text-orange-400 mb-4" />
            <p className="text-3xl font-black">{isBillsLoading ? '...' : formatNumber(stats.activePetitions)}</p>
            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mt-1">Active Petitions</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <section className="lg:col-span-2 bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
            <div className="p-6 border-b border-slate-700 font-bold flex items-center justify-between gap-4">
              <span>Live Bill Management</span>
              <span className="text-xs text-slate-400 uppercase tracking-widest">
                {isBillsLoading ? 'Loading bills...' : `${stats.activeBills} active`}
              </span>
            </div>

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
                {bills.map((bill) => (
                  <tr key={bill.id} className="hover:bg-slate-700/30 transition">
                    <td className="p-4 font-bold text-sm">
                      <div>{bill.title}</div>
                      {bill.sponsor && <div className="text-[11px] font-medium text-slate-400 mt-1">Sponsor: {bill.sponsor}</div>}
                    </td>
                    <td className="p-4 text-xs">
                      <select
                        className="bg-slate-900 border border-slate-600 rounded px-2 py-1 outline-none disabled:cursor-not-allowed disabled:opacity-50"
                        value={bill.status}
                        onChange={(e) => updateStatus(bill.id, e.target.value)}
                        disabled={!canUseProtectedActions}
                      >
                        <option>First Reading</option>
                        <option>Committee</option>
                        <option>Second Reading</option>
                        <option>Third Reading</option>
                        <option>Presidential Assent</option>
                      </select>
                    </td>
                    <td className="p-4 text-sm font-mono">{formatNumber(bill.subscriberCount ?? 0)}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => triggerSMS(bill.id, bill.title)}
                        disabled={isSending === bill.id || !canUseProtectedActions}
                        className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 ml-auto disabled:cursor-not-allowed disabled:opacity-60 ${
                          isSending === bill.id ? 'bg-slate-600' : 'bg-emerald-600 hover:bg-emerald-500'
                        } transition`}
                      >
                        <Send size={14} /> {isSending === bill.id ? 'Sending...' : 'Broadcast SMS'}
                      </button>
                    </td>
                  </tr>
                ))}
                {!isBillsLoading && bills.length === 0 && (
                  <tr>
                    <td className="p-6 text-slate-400 text-sm" colSpan={4}>
                      No live bills are available yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <AlertCircle size={18} className="text-indigo-400" /> System Logs
            </h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {!canUseProtectedActions && !isLogsLoading && (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-400">
                  Connect admin credentials above to load system logs.
                </div>
              )}
              {isLogsLoading && <div className="text-sm text-slate-400">Loading logs...</div>}
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="text-[11px] font-mono p-3 bg-slate-900 rounded border border-slate-700 text-slate-300"
                >
                  <span className="text-slate-600 mr-2">[{new Date(log.createdAt).toLocaleTimeString()}]</span>
                  {log.message}
                </div>
              ))}
              {!isLogsLoading && canUseProtectedActions && logs.length === 0 && (
                <div className="text-sm text-slate-400">No logs available yet.</div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
