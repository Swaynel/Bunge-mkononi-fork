'use client';

import { ChangeEvent, FormEvent, useState } from 'react';
import { CheckCircle, MessageSquare, Phone } from 'lucide-react';
import { postVote, trackSubscription } from '@/lib/api';
import { formatKenyanPhoneNumber, normalizeKenyanPhoneNumber } from '@/lib/phone';
import { PollChoice, PollTally } from '@/types';

interface Props {
  billId: string;
  billTitle: string;
  initialSignatureCount: number;
  initialPolling?: PollTally;
}

const OPTIONS: Array<{ label: string; choice: PollChoice }> = [
  { label: 'Yes, I support', choice: 'support' },
  { label: 'No, I oppose', choice: 'oppose' },
  { label: 'I need more info', choice: 'need_more_info' },
];

export default function ParticipationHub({
  billId,
  billTitle,
  initialSignatureCount,
  initialPolling = { yes: 0, no: 0, undecided: 0 },
}: Props) {
  const [hasVoted, setHasVoted] = useState(false);
  const [votedOption, setVotedOption] = useState('');
  const [signatureCount, setSignatureCount] = useState(initialSignatureCount);
  const [polling, setPolling] = useState<PollTally>(initialPolling);
  const [isIncrementing, setIsIncrementing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [subscriptionMessage, setSubscriptionMessage] = useState<string | null>(null);
  const [subscriptionError, setSubscriptionError] = useState<string | null>(null);

  const getSubscriptionErrorMessage = (subscriptionErrorValue: unknown) => {
    if (subscriptionErrorValue instanceof Error && subscriptionErrorValue.message) {
      return subscriptionErrorValue.message;
    }

    return 'We could not save your subscription right now. Please try again.';
  };

  const handleVote = async (optionLabel: string, choice: PollChoice) => {
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await postVote({ billId, choice });
      setVotedOption(optionLabel);
      setHasVoted(true);

      if (choice === 'support') {
        setIsIncrementing(true);
        setSignatureCount((current) =>
          typeof response.petitionSignatureCount === 'number' ? response.petitionSignatureCount : current + 1,
        );
        setTimeout(() => setIsIncrementing(false), 300);
      }

      setPolling((current) => {
        if (choice === 'support') {
          return { ...current, yes: current.yes + 1 };
        }
        if (choice === 'oppose') {
          return { ...current, no: current.no + 1 };
        }
        return { ...current, undecided: current.undecided + 1 };
      });
    } catch (voteError) {
      console.error(voteError);
      setError('We could not submit your vote right now. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubscriptionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubscriptionError(null);
    setSubscriptionMessage(null);

    const normalizedPhoneNumber = normalizeKenyanPhoneNumber(phoneNumber);

    if (!normalizedPhoneNumber) {
      setSubscriptionError('Enter a valid Kenyan phone number so we can send this bill’s SMS updates.');
      return;
    }

    setIsSubscribing(true);
    const displayPhoneNumber = phoneNumber || normalizedPhoneNumber;

    try {
      const response = await trackSubscription({
        billId,
        phoneNumber: normalizedPhoneNumber,
        channel: 'sms',
      });

      setPhoneNumber('');
      setSubscriptionMessage(
        response.created
          ? `Subscribed ${displayPhoneNumber} to ${billTitle} alerts.`
          : `${displayPhoneNumber} is already subscribed to ${billTitle} alerts.`,
      );
    } catch (subscriptionErrorValue) {
      console.error(subscriptionErrorValue);
      setSubscriptionError(getSubscriptionErrorMessage(subscriptionErrorValue));
    } finally {
      setIsSubscribing(false);
    }
  };

  return (
    <div className="mt-8 space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
          <p className="eyebrow text-slate-500">Supporters</p>
          <p
            className={`metric-mono mt-3 text-2xl font-semibold text-slate-900 transition duration-300 ${
              isIncrementing ? 'scale-105 text-brand-strong' : 'scale-100'
            }`}
          >
            {signatureCount.toLocaleString()}
          </p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">Live signature count</p>
        </div>
        <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
          <p className="eyebrow text-slate-500">Support</p>
          <p className="metric-mono mt-3 text-2xl font-semibold text-slate-900">{polling.yes.toLocaleString()}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">Votes in favor</p>
        </div>
        <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
          <p className="eyebrow text-slate-500">Oppose</p>
          <p className="metric-mono mt-3 text-2xl font-semibold text-slate-900">{polling.no.toLocaleString()}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">Votes against</p>
        </div>
        <div className="surface-panel p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-(--shadow-soft)">
          <p className="eyebrow text-slate-500">Need Info</p>
          <p className="metric-mono mt-3 text-2xl font-semibold text-slate-900">{polling.undecided.toLocaleString()}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">Undecided responses</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <section className="surface-card p-6">
          <div className="flex flex-col gap-4 border-b border-slate-200 pb-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="eyebrow text-brand-strong">Public Opinion Poll</p>
              <h3 className="font-[family:var(--font-site-serif)] text-2xl font-semibold text-slate-900">Submit A Structured Response</h3>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-600">
                Choose the position that best reflects your reading of the bill. Each response updates the public participation register.
              </p>
            </div>
            <div className="flex -space-x-2">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-slate-200 text-[10px] font-bold text-slate-500"
                >
                  {String.fromCharCode(64 + i)}
                </div>
              ))}
              <div className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-brand text-[10px] font-bold text-white">
                +12
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-3 gap-3 text-center">
            <div className="rounded-xl bg-brand-soft p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-strong">Support</p>
              <p className="metric-mono mt-1 text-lg font-semibold text-brand-strong">{polling.yes}</p>
            </div>
            <div className="rounded-xl bg-rose-50 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-rose-700">Oppose</p>
              <p className="metric-mono mt-1 text-lg font-semibold text-rose-700">{polling.no}</p>
            </div>
            <div className="rounded-xl bg-amber-50 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-amber-700">Need Info</p>
              <p className="metric-mono mt-1 text-lg font-semibold text-amber-700">{polling.undecided}</p>
            </div>
          </div>

          {!hasVoted ? (
            <div className="mt-6 animate-in fade-in duration-500">
              <p className="text-sm leading-7 text-slate-600">
                Do you support the clauses in {billTitle}? Your response helps inform the public record and the next
                citizen action.
              </p>
              <div className="mt-5 space-y-3">
                {OPTIONS.map((option) => (
                  <button
                    key={option.choice}
                    type="button"
                    onClick={() => handleVote(option.label, option.choice)}
                    disabled={isSubmitting}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-4 text-left text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:bg-slate-50 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmitting ? 'Submitting your vote...' : option.label}
                  </button>
                ))}
              </div>
              {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
            </div>
          ) : (
            <div className="mt-8 flex flex-col items-center justify-center rounded-xl border border-brand/15 bg-brand-soft/60 px-6 py-10 text-center animate-in zoom-in duration-300">
              <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-brand text-white shadow-lg shadow-brand/20">
                <CheckCircle size={40} />
              </div>
              <h4 className="text-2xl font-semibold text-foreground">Response Shared</h4>
              <p className="mt-2 text-sm text-slate-500">
                You chose <span className="font-semibold text-brand-strong">{votedOption}</span>
              </p>
              <button
                onClick={() => setHasVoted(false)}
                className="mt-6 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400 underline underline-offset-4 transition hover:text-brand-strong"
              >
                Edit Response
              </button>
            </div>
          )}
        </section>

        <section className="surface-card p-6">
          <div className="border-b border-slate-200 pb-4">
            <h3 className="flex items-center gap-2 font-[family:var(--font-site-serif)] text-2xl font-semibold text-foreground">
              <Phone className="text-brand" size={18} />
              Notification Register
            </h3>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Register a phone number for bill alerts or use the offline public channels below for lower-bandwidth access.
            </p>
          </div>

          <div className="mt-6 space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">USSD</p>
              <p className="metric-mono mt-2 text-lg font-semibold text-foreground">*384*16250#</p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-500">Open the menu and subscribe from any phone</p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">SMS</p>
              <p className="metric-mono mt-2 text-lg font-semibold text-foreground">TRACK {billId}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-500">Send to start receiving bill updates</p>
            </div>
          </div>

          <form onSubmit={handleSubscriptionSubmit} className="mt-6 space-y-3">
            <label className="block text-sm font-semibold text-foreground" htmlFor={`phone-${billId}`}>
              Subscribe With Your Phone Number
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                id={`phone-${billId}`}
                value={phoneNumber}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setPhoneNumber(formatKenyanPhoneNumber(e.target.value))}
                inputMode="tel"
                autoComplete="tel"
                placeholder="0712 345 678"
                className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
              />
              <button
                type="submit"
                disabled={isSubscribing}
                className="rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubscribing ? 'Saving...' : 'Subscribe'}
              </button>
            </div>
            <p className="text-[10px] font-medium uppercase tracking-[0.24em] text-slate-500">
              By subscribing, you consent to receive bill updates via SMS.
            </p>
          </form>

          <div className="mt-4 min-h-[2.5rem]">
            {subscriptionMessage && (
              <div className="inline-flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
                <CheckCircle size={16} /> {subscriptionMessage}
              </div>
            )}
            {subscriptionError && (
              <div className="inline-flex items-center gap-2 rounded-xl bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
                <MessageSquare size={16} /> {subscriptionError}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
