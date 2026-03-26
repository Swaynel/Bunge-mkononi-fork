'use client';

import { ChangeEvent, FormEvent, useState } from 'react';
import { CheckCircle, MessageSquare, Phone, Users, Vote } from 'lucide-react';
import { postVote, trackSubscription } from '@/lib/api';
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

function extractDigits(value: string) {
  return value.replace(/\D/g, '');
}

function formatKenyanPhoneNumber(value: string) {
  const trimmed = value.trim();
  const digits = extractDigits(trimmed);

  if (!digits && !trimmed.includes('+')) {
    return '';
  }

  const internationalMode = trimmed.startsWith('+') || digits.startsWith('254');
  const nationalDigits = internationalMode
    ? (digits.startsWith('254') ? digits.slice(3) : digits).slice(0, 9)
    : (digits.startsWith('0') ? digits.slice(1) : digits).slice(0, 9);

  if (internationalMode) {
    if (!nationalDigits) {
      return '+254';
    }

    const parts = [nationalDigits.slice(0, 3), nationalDigits.slice(3, 6), nationalDigits.slice(6, 9)].filter(Boolean);
    return `+254 ${parts.join(' ')}`;
  }

  const localDigits = (digits.startsWith('0') ? digits.slice(0, 10) : `0${digits}`).slice(0, 10);
  const localParts = [localDigits.slice(0, 4), localDigits.slice(4, 7), localDigits.slice(7, 10)].filter(Boolean);
  return localParts.join(' ');
}

function normalizeKenyanPhoneNumber(value: string) {
  const digits = extractDigits(value);
  if (!digits) {
    return '';
  }

  const nationalDigits = digits.startsWith('254')
    ? digits.slice(3, 12)
    : digits.startsWith('0')
      ? digits.slice(1, 10)
      : digits.slice(0, 9);

  if (nationalDigits.length !== 9) {
    return '';
  }

  return `+254${nationalDigits}`;
}

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
    <div className="mt-12 space-y-6">
      <div className="rounded-[2rem] border border-slate-200 bg-surface/95 p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand-strong">
              <Users size={20} />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-slate-500">Live support</p>
              <p
                className={`text-3xl font-semibold tracking-tight text-foreground transition duration-300 ${
                  isIncrementing ? 'scale-110 text-brand-strong' : 'scale-100'
                }`}
              >
                {signatureCount.toLocaleString()}
              </p>
            </div>
          </div>

          <div className="flex -space-x-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-surface bg-slate-200 text-[10px] font-bold text-slate-500"
              >
                {String.fromCharCode(64 + i)}
              </div>
            ))}
            <div className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-surface bg-brand text-[10px] font-bold text-white">
              +12
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <div className="rounded-[2rem] border border-slate-200 bg-surface/95 p-6 shadow-sm">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <Vote className="text-brand-strong" size={18} />
            Public opinion poll
          </h3>

          <div className="mt-5 grid grid-cols-3 gap-3 text-center">
            <div className="rounded-[1.25rem] bg-brand-soft p-3">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-brand-strong">Support</p>
              <p className="mt-1 text-lg font-semibold text-brand-strong">{polling.yes}</p>
            </div>
            <div className="rounded-[1.25rem] bg-rose-50 p-3">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-rose-700">Oppose</p>
              <p className="mt-1 text-lg font-semibold text-rose-700">{polling.no}</p>
            </div>
            <div className="rounded-[1.25rem] bg-amber-50 p-3">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-amber-700">Need info</p>
              <p className="mt-1 text-lg font-semibold text-amber-700">{polling.undecided}</p>
            </div>
          </div>

          {!hasVoted ? (
            <div className="mt-6 animate-in fade-in duration-500">
              <p className="text-sm leading-6 text-slate-500">
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
                    className="w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-4 text-left text-sm font-semibold text-slate-700 transition hover:border-brand/20 hover:bg-brand-soft/30 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmitting ? 'Submitting your vote...' : option.label}
                  </button>
                ))}
              </div>
              {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
            </div>
          ) : (
            <div className="mt-8 flex flex-col items-center justify-center rounded-[1.75rem] border border-brand/15 bg-brand-soft/60 px-6 py-10 text-center animate-in zoom-in duration-300">
              <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-brand text-white shadow-lg shadow-brand/20">
                <CheckCircle size={40} />
              </div>
              <h4 className="text-2xl font-semibold text-foreground">Response shared</h4>
              <p className="mt-2 text-sm text-slate-500">
                You chose <span className="font-semibold text-brand-strong">{votedOption}</span>
              </p>
              <button
                onClick={() => setHasVoted(false)}
                className="mt-6 text-xs font-bold uppercase tracking-[0.25em] text-slate-400 underline underline-offset-4 transition hover:text-brand-strong"
              >
                Edit response
              </button>
            </div>
          )}
        </div>

        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <Phone className="text-brand" size={18} />
            Offline participation
          </h3>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            SMS and USSD keep this bill available to people on basic phones and weaker networks.
          </p>

          <div className="mt-6 space-y-3">
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">USSD</p>
              <p className="mt-2 font-mono text-lg font-semibold text-foreground">*384*16250#</p>
              <p className="mt-2 text-xs text-slate-600">Open the menu and subscribe from any phone.</p>
            </div>

            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">SMS</p>
              <p className="mt-2 font-mono text-lg font-semibold text-foreground">TRACK {billId}</p>
              <p className="mt-2 text-xs text-slate-600">Send your number to start receiving bill updates.</p>
            </div>
          </div>

          <form onSubmit={handleSubscriptionSubmit} className="mt-6 space-y-3">
            <label className="block text-sm font-semibold text-foreground" htmlFor={`phone-${billId}`}>
              Subscribe with your phone number
            </label>
            <div className="flex gap-2">
              <input
                id={`phone-${billId}`}
                value={phoneNumber}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setPhoneNumber(formatKenyanPhoneNumber(e.target.value))}
                inputMode="tel"
                autoComplete="tel"
                placeholder="0712 345 678"
                className="flex-1 rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-foreground outline-none placeholder:text-slate-400 focus:border-brand/40 focus:ring-4 focus:ring-brand/10"
              />
              <button
                type="submit"
                disabled={isSubscribing}
                className="rounded-[1.25rem] bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubscribing ? 'Saving...' : 'Subscribe'}
              </button>
            </div>
            <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-slate-500">
              By subscribing, you consent to receive bill updates via SMS.
            </p>
          </form>

          <div className="mt-4 min-h-[2.5rem]">
            {subscriptionMessage && (
              <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
                <CheckCircle size={16} /> {subscriptionMessage}
              </div>
            )}
            {subscriptionError && (
              <div className="inline-flex items-center gap-2 rounded-[1.25rem] bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
                <MessageSquare size={16} /> {subscriptionError}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
