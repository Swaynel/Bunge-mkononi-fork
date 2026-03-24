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
          typeof response.petitionSignatureCount === 'number'
            ? response.petitionSignatureCount
            : current + 1,
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
    <div className="space-y-6 mt-12">
      <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Users className="text-orange-600" size={20} />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-tight">Live Support</p>
            <p
              className={`text-2xl font-black text-slate-900 transition-all duration-300 ${
                isIncrementing ? 'scale-110 text-emerald-600' : 'scale-100'
              }`}
            >
              {signatureCount.toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex -space-x-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-400">
              {String.fromCharCode(64 + i)}
            </div>
          ))}
          <div className="w-8 h-8 rounded-full border-2 border-white bg-indigo-600 flex items-center justify-center text-[10px] font-bold text-white">
            +12
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm min-h-87.5 flex flex-col justify-center">
          <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
            <Vote className="text-indigo-600" /> Public Opinion Poll
          </h3>

          <div className="grid grid-cols-3 gap-3 mb-6 text-center">
            <div className="rounded-xl bg-emerald-50 p-3">
              <p className="text-[10px] uppercase font-black text-emerald-700">Support</p>
              <p className="text-lg font-black text-emerald-700">{polling.yes}</p>
            </div>
            <div className="rounded-xl bg-rose-50 p-3">
              <p className="text-[10px] uppercase font-black text-rose-700">Oppose</p>
              <p className="text-lg font-black text-rose-700">{polling.no}</p>
            </div>
            <div className="rounded-xl bg-amber-50 p-3">
              <p className="text-[10px] uppercase font-black text-amber-700">Need info</p>
              <p className="text-lg font-black text-amber-700">{polling.undecided}</p>
            </div>
          </div>

          {!hasVoted ? (
            <div className="animate-in fade-in duration-500">
              <p className="text-sm text-slate-500 mb-6">
                Do you support the clauses in {billTitle}? Your vote helps inform your representative.
              </p>
              <div className="space-y-3">
                {OPTIONS.map((option) => (
                  <button
                    key={option.choice}
                    type="button"
                    onClick={() => handleVote(option.label, option.choice)}
                    disabled={isSubmitting}
                    className="w-full text-left p-4 rounded-xl border border-slate-200 hover:border-indigo-600 hover:bg-indigo-50 transition-all font-semibold text-slate-700 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? 'Submitting your vote...' : option.label}
                  </button>
                ))}
              </div>
              {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center animate-in zoom-in duration-300">
              <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-emerald-100">
                <CheckCircle size={40} />
              </div>
              <h4 className="text-2xl font-black text-slate-900">Response Shared!</h4>
              <p className="text-sm text-slate-500 mt-2">
                You chose: <span className="font-bold text-indigo-600">{votedOption}</span>
              </p>
              <button
                onClick={() => setHasVoted(false)}
                className="mt-6 text-xs font-bold text-slate-400 hover:text-indigo-600 underline underline-offset-4"
              >
                Edit my response
              </button>
            </div>
          )}
        </div>

        <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
              <Phone className="text-emerald-400" /> Offline Participation
            </h3>
            <p className="text-slate-400 text-sm mb-6">
              Using Africa&apos;s Talking USSD and SMS APIs to ensure every Kenyan&apos;s voice is heard, regardless of internet access.
            </p>
          </div>

          <div className="space-y-4">
            <div className="p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition">
              <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Global USSD Code</p>
              <p className="text-2xl font-mono text-emerald-400 mt-1 font-bold">*384*16250#</p>
            </div>

            <div className="p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">SMS Gateway</p>
                  <p className="text-sm mt-1">
                    Text <span className="font-bold text-emerald-400">TRACK {billId}</span> to <span className="font-bold text-emerald-400">22334</span>
                  </p>
                </div>
                <MessageSquare size={20} className="text-slate-600" />
              </div>
            </div>

            <form onSubmit={handleSubscriptionSubmit} className="p-4 bg-emerald-500/10 rounded-xl border border-emerald-400/20 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] text-emerald-200/80 uppercase font-black tracking-widest">Bill Subscription</p>
                  <p className="text-sm text-slate-200 mt-1">
                    Add your number and we&apos;ll send this bill&apos;s broadcast updates straight to your phone.
                  </p>
                </div>
                <Users size={18} className="text-emerald-300/80 shrink-0 mt-0.5" />
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel-national"
                  value={phoneNumber}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => setPhoneNumber(formatKenyanPhoneNumber(event.target.value))}
                  placeholder="0712 345 678"
                  className="flex-1 rounded-xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-emerald-400/70"
                />
                <button
                  type="submit"
                  disabled={isSubscribing}
                  className="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-4 py-3 text-sm font-bold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubscribing ? 'Saving...' : 'Subscribe'}
                </button>
              </div>

              <p className="text-[11px] text-slate-400">
                Kenyan numbers auto-format as you type. We only use this number for bill alerts from this tracker, and
                your subscription is tied to {billTitle}.
              </p>

              {subscriptionMessage && <p className="text-sm font-medium text-emerald-300">{subscriptionMessage}</p>}
              {subscriptionError && <p className="text-sm font-medium text-rose-300">{subscriptionError}</p>}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
