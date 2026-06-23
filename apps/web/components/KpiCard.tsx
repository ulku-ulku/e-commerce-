export function KpiCard({
  label, value, delta, suffix,
}: { label: string; value: string; delta?: number; suffix?: string }) {
  const up = (delta ?? 0) >= 0;
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-2xl font-bold mt-1">
        {value}
        {suffix && <span className="text-base font-normal text-slate-400 ml-1">{suffix}</span>}
      </p>
      {delta !== undefined && (
        <p className={`text-sm mt-1 ${up ? "text-green-600" : "text-red-600"}`}>
          {up ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
        </p>
      )}
    </div>
  );
}
