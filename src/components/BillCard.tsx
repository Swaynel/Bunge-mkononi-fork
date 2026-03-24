import Link from 'next/link';
import { Bill, Petition } from '@/types';

interface Props {
  bill: Bill;
  petition?: Petition;
}

export default function BillCard({ bill, petition }: Props) {
  const progressPercent = petition ? (petition.signatureCount / petition.goal) * 100 : 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition flex flex-col h-full">
      <div className="p-5 flex-1">
        <div className="flex justify-between items-start mb-3">
          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded uppercase tracking-wider">
            {bill.category}
          </span>
          <span className="text-sm font-medium text-slate-500">{bill.status}</span>
        </div>
        
        {/* Title links to the detail page */}
        <Link href={`/bill/${bill.id}`}>
          <h3 className="text-lg font-bold text-slate-900 mb-2 hover:text-indigo-600 transition cursor-pointer">
            {bill.title}
          </h3>
        </Link>
        
        <p className="text-slate-600 text-sm mb-4 line-clamp-2">{bill.summary}</p>

        {petition && (
          <div className="space-y-3">
            <div className="flex justify-between text-xs font-semibold">
              <span className="text-slate-500">Signatures</span>
              <span className="text-orange-600">
                {petition.signatureCount.toLocaleString()} / {petition.goal.toLocaleString()}
              </span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full">
              <div 
                className="bg-orange-500 h-2 rounded-full transition-all" 
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}
      </div>
      
      <div className="bg-slate-50 p-4 border-t border-slate-200 flex gap-2">
        {/* Primary Action: View Details */}
        <Link href={`/bill/${bill.id}`} className="flex-1">
          <button className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition">
            View Details
          </button>
        </Link>
        
        <button className="flex-1 bg-white border border-slate-300 text-slate-700 py-2 rounded-lg text-sm font-semibold hover:bg-slate-50 transition">
          Track via SMS
        </button>
      </div>
    </div>
  );
}