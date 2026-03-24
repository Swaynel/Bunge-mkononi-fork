'use client';

import { useState, useEffect } from 'react';
import { Vote, Phone, MessageSquare, CheckCircle, Users } from 'lucide-react';

export default function ParticipationHub({ billId }: { billId: string }) {
 
  const [hasVoted, setHasVoted] = useState(false);
  const [votedOption, setVotedOption] = useState('');
  

  const [signatureCount, setSignatureCount] = useState(8450);
  const [isIncrementing, setIsIncrementing] = useState(false);


  const handleVote = (option: string) => {
    setVotedOption(option);
    setHasVoted(true);

   
    if (option === 'Yes, I support') {
      setIsIncrementing(true);
      setTimeout(() => {
        setSignatureCount(prev => prev + 1);
        setIsIncrementing(false);
      }, 300);
    }
  };

  return (
    <div className="space-y-6 mt-12">
      {/* LIVE COUNTER STRIP */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Users className="text-orange-600" size={20} />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-tight">Live Support</p>
            <p className={`text-2xl font-black text-slate-900 transition-all duration-300 ${isIncrementing ? 'scale-110 text-emerald-600' : 'scale-100'}`}>
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
        {/* Polling Section */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm min-h-87.5 flex flex-col justify-center">
          <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
            <Vote className="text-indigo-600" /> Public Opinion Poll
          </h3>
          
          {!hasVoted ? (
            <div className="animate-in fade-in duration-500">
              <p className="text-sm text-slate-500 mb-6">Do you support the clauses in this bill? Your vote helps inform your representative.</p>
              <div className="space-y-3">
                {['Yes, I support', 'No, I oppose', 'I need more info'].map((option) => (
                  <button 
                    key={option} 
                    type="button"
                    onClick={() => handleVote(option)}
                    className="w-full text-left p-4 rounded-xl border border-slate-200 hover:border-indigo-600 hover:bg-indigo-50 transition-all font-semibold text-slate-700 active:scale-[0.98]"
                  >
                    {option}
                  </button>
                ))}
              </div>
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

        {/* AT Integration Section (Africa's Talking) */}
        <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold flex items-center gap-2 mb-4">
              <Phone className="text-emerald-400" /> Offline Participation
            </h3>
            <p className="text-slate-400 text-sm mb-6">Using Africa's Talking USSD and SMS APIs to ensure every Kenyan's voice is heard, regardless of internet access.</p>
          </div>
          
          <div className="space-y-4">
            <div className="p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition">
              <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Global USSD Code</p>
              <p className="text-2xl font-mono text-emerald-400 mt-1 font-bold">*384*100#</p>
            </div>
            
            <div className="p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition">
              <div className="flex justify-between items-center">
                 <div>
                    <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">SMS Gateway</p>
                    <p className="text-sm mt-1">Text <span className="font-bold text-emerald-400">TRACK {billId}</span> to <span className="font-bold text-emerald-400">22334</span></p>
                 </div>
                 <MessageSquare size={20} className="text-slate-600" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}