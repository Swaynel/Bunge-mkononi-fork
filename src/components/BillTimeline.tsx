// BillTimeline Redesign
'use client';

import { Check } from 'lucide-react';
import { BillStatus } from '@/types';

const STAGES: BillStatus[] = ['First Reading', 'Committee', 'Second Reading', 'Third Reading', 'Presidential Assent'];

export default function BillTimeline({ currentStage }: { currentStage: BillStatus }) {
  const currentIndex = Math.max(STAGES.indexOf(currentStage), 0);

  return (
    <section className="border-2 border-slate-900 bg-white p-8">
      <div className="mb-10 flex flex-col gap-2 border-b-2 border-slate-900 pb-4">
        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-brand-strong">Process Tracking</p>
        <h3 className="text-2xl font-black tracking-tight text-slate-900">Legislative Journey</h3>
      </div>

      <div className="relative">
        {/* The Connection Line */}
        <div className="absolute top-5 left-0 h-1 w-full bg-slate-100 hidden lg:block" />
        
        <ol className="grid gap-6 lg:grid-cols-5 relative">
          {STAGES.map((stage, index) => {
            const isCompleted = index < currentIndex;
            const isCurrent = index === currentIndex;
            const isPending = index > currentIndex;

            return (
              <li key={stage} className="relative flex flex-col">
                {/* Node Circle */}
                <div className={`z-10 flex h-10 w-10 items-center justify-center border-2 transition-colors ${
                  isCurrent ? 'border-slate-900 bg-brand-strong text-white' :
                  isCompleted ? 'border-slate-900 bg-slate-900 text-white' : 
                  'border-slate-200 bg-white text-slate-300'
                }`}>
                  {isCompleted ? <Check size={20} /> : <span className="text-xs font-black">{index + 1}</span>}
                </div>

                {/* Content */}
                <div className={`mt-4 border-t-4 pt-4 ${isCurrent ? 'border-brand-strong' : 'border-transparent'}`}>
                  <p className={`text-xs font-black uppercase tracking-widest ${isPending ? 'text-slate-400' : 'text-slate-900'}`}>
                    {stage}
                  </p>
                  <p className="mt-1 text-[10px] font-bold text-slate-500 uppercase">
                    {isCurrent ? 'Active Now' : isCompleted ? 'Verified' : 'Scheduled'}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
