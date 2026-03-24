import { CheckCircle2, Circle } from 'lucide-react';
import { BillStatus } from '@/types';

const STAGES: BillStatus[] = ['First Reading', 'Committee', 'Second Reading', 'Third Reading', 'Presidential Assent'];

export default function BillTimeline({ currentStage }: { currentStage: BillStatus }) {
  const currentIndex = STAGES.indexOf(currentStage);

  return (
    <div className="py-8">
      <div className="flex items-center w-full">
        {STAGES.map((stage, idx) => (
          <div key={stage} className="flex flex-1 items-center last:flex-none">
            <div className="relative flex flex-col items-center group">
              {idx <= currentIndex ? (
                <CheckCircle2 className="w-8 h-8 text-green-600 bg-white" />
              ) : (
                <Circle className="w-8 h-8 text-slate-300 bg-white" />
              )}
              <div className="absolute top-10 w-24 text-center">
                <p className={`text-[10px] font-bold uppercase ${idx <= currentIndex ? 'text-slate-900' : 'text-slate-400'}`}>
                  {stage}
                </p>
              </div>
            </div>
            {idx < STAGES.length - 1 && (
              <div className={`flex-1 h-1 mx-2 ${idx < currentIndex ? 'bg-green-600' : 'bg-slate-200'}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}