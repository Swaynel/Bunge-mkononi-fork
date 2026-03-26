export default function Loading() {
  return (
    <div className="space-y-6">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="h-3 w-32 animate-pulse rounded-full bg-slate-200" />
        <div className="mt-4 h-10 w-3/4 animate-pulse rounded-full bg-slate-200" />
        <div className="mt-3 h-4 w-full animate-pulse rounded-full bg-slate-100" />
        <div className="mt-2 h-4 w-5/6 animate-pulse rounded-full bg-slate-100" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-sm">
            <div className="h-3 w-24 animate-pulse rounded-full bg-slate-200" />
            <div className="mt-4 h-8 w-20 animate-pulse rounded-full bg-slate-100" />
          </div>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div className="space-y-6">
          <div className="h-80 animate-pulse rounded-[2rem] border border-slate-200 bg-white shadow-sm" />
          <div className="h-96 animate-pulse rounded-[2rem] border border-slate-200 bg-white shadow-sm" />
        </div>
        <div className="space-y-6">
          <div className="h-72 animate-pulse rounded-[2rem] border border-slate-200 bg-white shadow-sm" />
          <div className="h-72 animate-pulse rounded-[2rem] border border-slate-200 bg-white shadow-sm" />
        </div>
      </div>
    </div>
  );
}
