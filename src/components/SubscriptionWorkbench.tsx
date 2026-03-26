'use client';

import Link from 'next/link';
import { ChangeEvent, FormEvent, useDeferredValue, useEffect, useState } from 'react';
import {
  BellRing,
  CheckCircle2,
  Languages,
  ListChecks,
  LoaderCircle,
  PauseCircle,
  PlayCircle,
  Search,
  Send,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react';
import { createSubscription, listBills, lookupSubscriptions, manageSubscription } from '@/lib/api';
import { formatKenyanPhoneNumber, normalizeKenyanPhoneNumber } from '@/lib/phone';
import type {
  Bill,
  BillCategory,
  MessageLanguage,
  SubscriptionCadence,
  SubscriptionRecord,
  SubscriptionScope,
  SubscriptionStatus,
} from '@/types';

const SCOPE_OPTIONS: Array<{ value: SubscriptionScope; label: string; helper: string }> = [
  { value: 'bill', label: 'Specific bill', helper: 'Mirror TRACK <bill> from SMS.' },
  { value: 'category', label: 'Category', helper: 'Mirror TRACK CATEGORY <category>.' },
  { value: 'county', label: 'County', helper: 'Mirror TRACK COUNTY <county>.' },
  { value: 'sponsor', label: 'Sponsor', helper: 'Mirror TRACK SPONSOR <name>.' },
  { value: 'all', label: 'All bills', helper: 'Mirror TRACK ALL.' },
];

const CATEGORY_OPTIONS: BillCategory[] = ['Finance', 'Health', 'Education', 'Justice', 'Environment'];

const LANGUAGE_OPTIONS: Array<{ value: MessageLanguage; label: string }> = [
  { value: 'en', label: 'English' },
  { value: 'sw', label: 'Kiswahili' },
];

const CADENCE_OPTIONS: Array<{ value: SubscriptionCadence; label: string }> = [
  { value: 'instant', label: 'Instant' },
  { value: 'daily', label: 'Daily digest' },
  { value: 'weekly', label: 'Weekly digest' },
  { value: 'milestone', label: 'Milestones only' },
];

const STATUS_ACTIONS: Record<'paused' | 'active' | 'unsubscribed', string> = {
  paused: 'Pause',
  active: 'Resume',
  unsubscribed: 'Stop',
};

type EditableSubscriptionFields = Pick<SubscriptionRecord, 'language' | 'cadence'>;

function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'We could not complete that request right now.';
}

function scopeLabel(scope: SubscriptionScope) {
  return SCOPE_OPTIONS.find((option) => option.value === scope)?.label ?? scope;
}

function cadenceLabel(cadence: SubscriptionCadence) {
  return CADENCE_OPTIONS.find((option) => option.value === cadence)?.label ?? cadence;
}

function languageLabel(language: MessageLanguage) {
  return LANGUAGE_OPTIONS.find((option) => option.value === language)?.label ?? language.toUpperCase();
}

export default function SubscriptionWorkbench({
  featuredBill,
}: {
  featuredBill?: Pick<Bill, 'id' | 'title'> | null;
}) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [scope, setScope] = useState<SubscriptionScope>('bill');
  const [selectedBill, setSelectedBill] = useState<Pick<Bill, 'id' | 'title'> | null>(featuredBill ?? null);
  const [billSearch, setBillSearch] = useState(featuredBill?.title ?? '');
  const [billResults, setBillResults] = useState<Array<Pick<Bill, 'id' | 'title'>>>([]);
  const [billSearchError, setBillSearchError] = useState<string | null>(null);
  const [categoryValue, setCategoryValue] = useState<BillCategory>('Finance');
  const [countyValue, setCountyValue] = useState('');
  const [sponsorValue, setSponsorValue] = useState('');
  const [language, setLanguage] = useState<MessageLanguage>('en');
  const [cadence, setCadence] = useState<SubscriptionCadence>('instant');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createMessage, setCreateMessage] = useState<string | null>(null);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [subscriptionDrafts, setSubscriptionDrafts] = useState<Record<number, EditableSubscriptionFields>>({});
  const [isLoadingSubscriptions, setIsLoadingSubscriptions] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupMessage, setLookupMessage] = useState<string | null>(null);
  const [activeSubscriptionId, setActiveSubscriptionId] = useState<number | null>(null);
  const [manageError, setManageError] = useState<string | null>(null);
  const [manageMessage, setManageMessage] = useState<string | null>(null);

  const deferredBillSearch = useDeferredValue(billSearch.trim());

  useEffect(() => {
    if (scope !== 'bill') {
      setBillResults([]);
      setBillSearchError(null);
      return;
    }

    const query = deferredBillSearch;
    if (!query || (selectedBill && query === selectedBill.title)) {
      setBillResults([]);
      setBillSearchError(null);
      return;
    }

    let active = true;

    listBills({
      search: query,
      ordering: '-is_hot,-date_introduced',
    })
      .then((response) => {
        if (!active) {
          return;
        }

        setBillResults(
          response.results.slice(0, 6).map((bill) => ({
            id: bill.id,
            title: bill.title,
          })),
        );
        setBillSearchError(null);
      })
      .catch((searchErrorValue) => {
        if (!active) {
          return;
        }

        console.error(searchErrorValue);
        setBillResults([]);
        setBillSearchError('We could not search bills right now.');
      });

    return () => {
      active = false;
    };
  }, [deferredBillSearch, scope, selectedBill]);

  const syncSubscriptionDrafts = (items: SubscriptionRecord[]) => {
    setSubscriptionDrafts(
      items.reduce<Record<number, EditableSubscriptionFields>>((drafts, subscription) => {
        drafts[subscription.id] = {
          language: subscription.language,
          cadence: subscription.cadence,
        };
        return drafts;
      }, {}),
    );
  };

  const loadSubscriptions = async (normalizedPhoneNumber: string) => {
    setIsLoadingSubscriptions(true);
    setLookupError(null);
    setManageError(null);

    try {
      const response = await lookupSubscriptions(normalizedPhoneNumber);
      setSubscriptions(response.subscriptions);
      syncSubscriptionDrafts(response.subscriptions);
      setLookupMessage(
        response.count > 0
          ? `Loaded ${response.count} active or paused watchlist${response.count === 1 ? '' : 's'} for ${normalizedPhoneNumber}.`
          : `No active or paused watchlists were found for ${normalizedPhoneNumber}.`,
      );
    } catch (lookupErrorValue) {
      console.error(lookupErrorValue);
      setLookupError(getErrorMessage(lookupErrorValue));
      setLookupMessage(null);
    } finally {
      setIsLoadingSubscriptions(false);
    }
  };

  const handlePhoneLookup = async () => {
    const normalizedPhoneNumber = normalizeKenyanPhoneNumber(phoneNumber);
    if (!normalizedPhoneNumber) {
      setLookupError('Enter a valid Kenyan phone number to load your watchlists.');
      setLookupMessage(null);
      return;
    }

    await loadSubscriptions(normalizedPhoneNumber);
  };

  const handleCreateSubscription = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError(null);
    setCreateMessage(null);
    setManageMessage(null);

    const normalizedPhoneNumber = normalizeKenyanPhoneNumber(phoneNumber);
    if (!normalizedPhoneNumber) {
      setCreateError('Enter a valid Kenyan phone number before creating a watchlist.');
      return;
    }

    let billId: string | undefined;
    let targetValue = '';

    if (scope === 'bill') {
      if (!selectedBill) {
        setCreateError('Search for a bill and choose it before creating a bill watchlist.');
        return;
      }
      billId = selectedBill.id;
    }

    if (scope === 'category') {
      targetValue = categoryValue;
    }

    if (scope === 'county') {
      targetValue = countyValue.trim();
    }

    if (scope === 'sponsor') {
      targetValue = sponsorValue.trim();
    }

    if ((scope === 'county' || scope === 'sponsor') && !targetValue) {
      setCreateError(`Enter a ${scope} before creating this watchlist.`);
      return;
    }

    setIsCreating(true);

    try {
      const response = await createSubscription({
        billId,
        phoneNumber: normalizedPhoneNumber,
        channel: 'sms',
        scope,
        targetValue,
        language,
        cadence,
      });

      const target = response.target || selectedBill?.title || targetValue || 'all bills';
      setCreateMessage(
        response.created
          ? `Saved ${target} for ${normalizedPhoneNumber}.`
          : `That watchlist already exists for ${normalizedPhoneNumber}.`,
      );

      if (subscriptions.length > 0) {
        await loadSubscriptions(normalizedPhoneNumber);
      }
    } catch (createErrorValue) {
      console.error(createErrorValue);
      setCreateError(getErrorMessage(createErrorValue));
    } finally {
      setIsCreating(false);
    }
  };

  const updateLocalSubscription = (nextSubscription: SubscriptionRecord) => {
    setSubscriptions((currentSubscriptions) => {
      if (nextSubscription.status === 'unsubscribed') {
        return currentSubscriptions.filter((subscription) => subscription.id !== nextSubscription.id);
      }

      return currentSubscriptions.map((subscription) =>
        subscription.id === nextSubscription.id ? nextSubscription : subscription,
      );
    });

    setSubscriptionDrafts((currentDrafts) => ({
      ...currentDrafts,
      [nextSubscription.id]: {
        language: nextSubscription.language,
        cadence: nextSubscription.cadence,
      },
    }));
  };

  const handleManageSubscription = async (
    subscription: SubscriptionRecord,
    payload: {
      status?: SubscriptionStatus;
      language?: MessageLanguage;
      cadence?: SubscriptionCadence;
    },
  ) => {
    const normalizedPhoneNumber = normalizeKenyanPhoneNumber(phoneNumber);
    if (!normalizedPhoneNumber) {
      setManageError('Enter the same Kenyan phone number used for your watchlists before making changes.');
      setManageMessage(null);
      return;
    }

    setActiveSubscriptionId(subscription.id);
    setManageError(null);
    setManageMessage(null);

    try {
      const updated = await manageSubscription(subscription.id, {
        phoneNumber: normalizedPhoneNumber,
        ...payload,
      });

      updateLocalSubscription(updated);
      setManageMessage(updated.message || `Updated ${updated.target}.`);
    } catch (manageErrorValue) {
      console.error(manageErrorValue);
      setManageError(getErrorMessage(manageErrorValue));
    } finally {
      setActiveSubscriptionId(null);
    }
  };

  const handlePreferenceDraftChange = (
    subscriptionId: number,
    field: keyof EditableSubscriptionFields,
    value: MessageLanguage | SubscriptionCadence,
  ) => {
    setSubscriptionDrafts((currentDrafts) => ({
      ...currentDrafts,
      [subscriptionId]: {
        ...(currentDrafts[subscriptionId] ?? { language: 'en', cadence: 'instant' }),
        [field]: value,
      },
    }));
  };

  const renderScopeControl = () => {
    if (scope === 'bill') {
      return (
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-foreground" htmlFor="watchlist-bill-search">
            Bill search
          </label>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              id="watchlist-bill-search"
              value={billSearch}
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const nextValue = event.target.value;
                setBillSearch(nextValue);
                if (selectedBill && nextValue.trim() !== selectedBill.title) {
                  setSelectedBill(null);
                }
              }}
              type="text"
              placeholder="Search by bill ID or title..."
              className="w-full rounded-[1.25rem] border border-slate-200 bg-white py-3 pl-12 pr-4 text-sm text-foreground outline-none transition placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
            />
          </div>

          {selectedBill && (
            <div className="flex items-center justify-between rounded-[1.25rem] border border-brand/15 bg-brand-soft/40 px-4 py-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-brand-strong">Selected bill</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{selectedBill.title}</p>
                <p className="metric-mono mt-1 text-xs text-slate-500">{selectedBill.id}</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedBill(null);
                  setBillSearch('');
                }}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-brand/20 hover:text-brand-strong"
              >
                Clear
              </button>
            </div>
          )}

          {billResults.length > 0 && !selectedBill && (
            <div className="rounded-[1.25rem] border border-slate-200 bg-white p-2">
              {billResults.map((bill) => (
                <button
                  key={bill.id}
                  type="button"
                  onClick={() => {
                    setSelectedBill(bill);
                    setBillSearch(bill.title);
                    setBillResults([]);
                  }}
                  className="flex w-full items-start justify-between rounded-xl px-3 py-3 text-left transition hover:bg-slate-50"
                >
                  <span>
                    <span className="block text-sm font-semibold text-foreground">{bill.title}</span>
                    <span className="metric-mono mt-1 block text-xs text-slate-500">{bill.id}</span>
                  </span>
                  <Send size={14} className="mt-1 text-slate-400" />
                </button>
              ))}
            </div>
          )}

          {billSearchError && <p className="text-sm text-rose-600">{billSearchError}</p>}
          {!selectedBill && featuredBill && !billSearch.trim() && (
            <p className="text-xs text-slate-500">
              Tip: the current featured bill is <span className="font-semibold text-slate-700">{featuredBill.title}</span>.
            </p>
          )}
        </div>
      );
    }

    if (scope === 'category') {
      return (
        <div>
          <label className="block text-sm font-semibold text-foreground" htmlFor="watchlist-category">
            Category
          </label>
          <select
            id="watchlist-category"
            value={categoryValue}
            onChange={(event) => setCategoryValue(event.target.value as BillCategory)}
            className="mt-3 w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none transition focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
          >
            {CATEGORY_OPTIONS.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (scope === 'county') {
      return (
        <div>
          <label className="block text-sm font-semibold text-foreground" htmlFor="watchlist-county">
            County
          </label>
          <input
            id="watchlist-county"
            value={countyValue}
            onChange={(event) => setCountyValue(event.target.value)}
            type="text"
            placeholder="Nairobi"
            className="mt-3 w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none transition placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
          />
        </div>
      );
    }

    if (scope === 'sponsor') {
      return (
        <div>
          <label className="block text-sm font-semibold text-foreground" htmlFor="watchlist-sponsor">
            Sponsor
          </label>
          <input
            id="watchlist-sponsor"
            value={sponsorValue}
            onChange={(event) => setSponsorValue(event.target.value)}
            type="text"
            placeholder="Hon. Alice Wanjiku"
            className="mt-3 w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none transition placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
          />
        </div>
      );
    }

    return (
      <div className="rounded-[1.25rem] border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
        This will follow every bill in the feed and mirror the SMS <span className="font-semibold">TRACK ALL</span> flow.
      </div>
    );
  };

  return (
    <section className="space-y-6">
      <div className="surface-card p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="eyebrow text-slate-500">Parity desk</p>
            <h2 className="mt-2 text-3xl font-semibold text-foreground">Web controls for the same SMS and USSD jobs.</h2>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Build the same watchlists, then pause, resume, stop, or retune them from the browser without dropping
              down to a handset menu.
            </p>
          </div>

          <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Use one Kenyan phone number across both panels so web actions map to the same subscriber record.
          </div>
        </div>

        <div className="mt-6 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
          <label className="block" htmlFor="watchlist-phone">
            <span className="block text-sm font-semibold text-foreground">Subscriber phone number</span>
            <input
              id="watchlist-phone"
              value={phoneNumber}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setPhoneNumber(formatKenyanPhoneNumber(event.target.value))}
              inputMode="tel"
              autoComplete="tel"
              placeholder="0712 345 678"
              className="mt-3 w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none transition placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
            />
          </label>

          <button
            type="button"
            onClick={handlePhoneLookup}
            disabled={isLoadingSubscriptions}
            className="inline-flex h-[52px] items-center justify-center gap-2 rounded-[1.25rem] border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong disabled:cursor-not-allowed disabled:opacity-60 lg:self-end"
          >
            {isLoadingSubscriptions ? <LoaderCircle size={16} className="animate-spin" /> : <ListChecks size={16} />}
            Load my watchlists
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
        <form onSubmit={handleCreateSubscription} className="surface-card p-6">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-soft text-brand-strong">
              <BellRing size={18} />
            </span>
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Create watchlist</p>
              <h3 className="text-xl font-semibold text-foreground">Mirror TRACK flows from the web</h3>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {SCOPE_OPTIONS.map((option) => {
              const active = scope === option.value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setScope(option.value)}
                  className={`rounded-[1.5rem] border px-4 py-4 text-left transition ${
                    active
                      ? 'border-brand/20 bg-brand-soft/60 shadow-(--shadow-soft)'
                      : 'border-slate-200 bg-white hover:border-brand/20 hover:bg-slate-50'
                  }`}
                >
                  <p className="text-sm font-semibold text-foreground">{option.label}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">{option.helper}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-6">{renderScopeControl()}</div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Languages size={14} className="text-slate-400" />
                Language
              </span>
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value as MessageLanguage)}
                className="mt-3 w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none transition focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <SlidersHorizontal size={14} className="text-slate-400" />
                Cadence
              </span>
              <select
                value={cadence}
                onChange={(event) => setCadence(event.target.value as SubscriptionCadence)}
                className="mt-3 w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none transition focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
              >
                {CADENCE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={isCreating}
              className="inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isCreating ? <LoaderCircle size={16} className="animate-spin" /> : <BellRing size={16} />}
              {isCreating ? 'Saving watchlist...' : 'Save watchlist'}
            </button>
            <Link
              href="/bills"
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong"
            >
              Browse bill details first
            </Link>
          </div>

          <div className="mt-4 min-h-[2.5rem]">
            {createMessage && (
              <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
                <CheckCircle2 size={16} /> {createMessage}
              </div>
            )}
            {createError && (
              <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
                <Trash2 size={16} /> {createError}
              </div>
            )}
          </div>
        </form>

        <div className="space-y-6">
          <section className="surface-card p-6">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-accent-soft text-accent">
                <ListChecks size={18} />
              </span>
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Manage subscriptions</p>
                <h3 className="text-xl font-semibold text-foreground">Pause, resume, stop, or retune alerts</h3>
              </div>
            </div>

            <div className="mt-5 min-h-[2.5rem] space-y-3">
              {lookupMessage && (
                <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">
                  <CheckCircle2 size={16} /> {lookupMessage}
                </div>
              )}
              {lookupError && (
                <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
                  <Trash2 size={16} /> {lookupError}
                </div>
              )}
              {manageMessage && (
                <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
                  <CheckCircle2 size={16} /> {manageMessage}
                </div>
              )}
              {manageError && (
                <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
                  <Trash2 size={16} /> {manageError}
                </div>
              )}
            </div>

            <div className="mt-6 space-y-4">
              {subscriptions.length > 0 ? (
                subscriptions.map((subscription) => {
                  const draft = subscriptionDrafts[subscription.id] ?? {
                    language: subscription.language,
                    cadence: subscription.cadence,
                  };
                  const isBusy = activeSubscriptionId === subscription.id;

                  return (
                    <article key={subscription.id} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="text-[10px] font-black uppercase tracking-[0.28em] text-slate-500">
                            {scopeLabel(subscription.scope)}
                          </p>
                          <h4 className="mt-2 text-lg font-semibold text-foreground">{subscription.target}</h4>
                          <p className="metric-mono mt-1 text-xs text-slate-500">
                            {subscription.billId || subscription.targetValue || 'All bills'}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className="rounded-full bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                            {subscription.status}
                          </span>
                          <span className="rounded-full bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                            {languageLabel(subscription.language)}
                          </span>
                          <span className="rounded-full bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                            {cadenceLabel(subscription.cadence)}
                          </span>
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <label className="block">
                          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Language</span>
                          <select
                            value={draft.language}
                            disabled={isBusy}
                            onChange={(event) =>
                              handlePreferenceDraftChange(subscription.id, 'language', event.target.value as MessageLanguage)
                            }
                            className="mt-2 w-full rounded-[1rem] border border-slate-200 bg-white px-3 py-2.5 text-sm text-foreground outline-none transition focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
                          >
                            {LANGUAGE_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>

                        <label className="block">
                          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Cadence</span>
                          <select
                            value={draft.cadence}
                            disabled={isBusy}
                            onChange={(event) =>
                              handlePreferenceDraftChange(subscription.id, 'cadence', event.target.value as SubscriptionCadence)
                            }
                            className="mt-2 w-full rounded-[1rem] border border-slate-200 bg-white px-3 py-2.5 text-sm text-foreground outline-none transition focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
                          >
                            {CADENCE_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() =>
                            handleManageSubscription(subscription, {
                              language: draft.language,
                              cadence: draft.cadence,
                            })
                          }
                          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:text-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isBusy ? <LoaderCircle size={14} className="animate-spin" /> : <SlidersHorizontal size={14} />}
                          Save preferences
                        </button>

                        {subscription.status !== 'paused' && (
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => handleManageSubscription(subscription, { status: 'paused' })}
                            className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 transition hover:border-amber-300 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <PauseCircle size={14} />
                            {STATUS_ACTIONS.paused}
                          </button>
                        )}

                        {subscription.status === 'paused' && (
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => handleManageSubscription(subscription, { status: 'active' })}
                            className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800 transition hover:border-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <PlayCircle size={14} />
                            {STATUS_ACTIONS.active}
                          </button>
                        )}

                        <button
                          type="button"
                          disabled={isBusy}
                          onClick={() => handleManageSubscription(subscription, { status: 'unsubscribed' })}
                          className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:border-rose-300 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <Trash2 size={14} />
                          {STATUS_ACTIONS.unsubscribed}
                        </button>
                      </div>
                    </article>
                  );
                })
              ) : (
                <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-white px-4 py-6 text-sm text-slate-600">
                  Load a phone number above to view the active and paused watchlists tied to it.
                </div>
              )}
            </div>
          </section>

          <section className="surface-card bg-slate-900 p-6 text-white">
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Coverage map</p>
            <h3 className="mt-3 text-2xl font-semibold">What now has a web route</h3>
            <div className="mt-5 space-y-4 text-sm leading-7 text-slate-300">
              <p>
                <span className="font-semibold text-white">TRACK, TRACK CATEGORY, TRACK COUNTY, TRACK SPONSOR, TRACK ALL</span>
                {' '}map to the watchlist builder here.
              </p>
              <p>
                <span className="font-semibold text-white">LIST, PAUSE, RESUME, STOP, LANG</span>
                {' '}map to the subscription manager in this panel.
              </p>
              <p>
                <span className="font-semibold text-white">STATUS, SUMMARY, DOCUMENT, IMPACT, TIMELINE, VOTES, SIGN</span>
                {' '}already map to the bill pages and participation tools across the site.
              </p>
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
