import { MapPin } from 'lucide-react';

const COUNTY_DATA = [
  { name: 'Nairobi', signatures: 4500, sentiment: 'Oppose' },
  { name: 'Mombasa', signatures: 2100, sentiment: 'Mixed' },
  { name: 'Kisumu', signatures: 1800, sentiment: 'Oppose' },
  { name: 'Nakuru', signatures: 1200, sentiment: 'Support' },
];

export default function RegionalImpact() {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
      <h3 className="text-lg font-bold flex items-center gap-2 mb-6">
        <MapPin className="text-rose-500" /> Regional Engagement
      </h3>
      
      <div className="space-y-6">
        {COUNTY_DATA.map((county) => (
          <div key={county.name}>
            <div className="flex justify-between items-end mb-2">
              <div>
                <span className="text-sm font-bold text-slate-900">{county.name}</span>
                <span className={`ml-2 text-[10px] uppercase font-black ${
                  county.sentiment === 'Oppose' ? 'text-rose-500' : 
                  county.sentiment === 'Support' ? 'text-emerald-500' : 'text-amber-500'
                }`}>
                  • {county.sentiment}
                </span>
              </div>
              <span className="text-xs text-slate-500 font-medium">{county.signatures.toLocaleString()} voices</span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ${
                  county.sentiment === 'Oppose' ? 'bg-rose-500' : 
                  county.sentiment === 'Support' ? 'bg-emerald-500' : 'bg-amber-500'
                }`}
                style={{ width: `${(county.signatures / 5000) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}