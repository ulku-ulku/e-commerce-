"use client";
import { useEffect, useState } from "react";
import { api, type GrowthData, type GrowthRow } from "@/lib/api";

const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");
const pct = (n: number) => `${n >= 0 ? "+" : ""}${n}%`;
const tone = (n: number) => (n > 0 ? "text-emerald-600" : n < 0 ? "text-red-600" : "text-slate-400");

function Row({ r, label }: { r: GrowthRow; label: string }) {
  const up = r.change_pct >= 0;
  const w = Math.min(100, Math.abs(r.change_pct));
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-24 truncate text-slate-600">{label}</span>
      <div className="flex-1 flex items-center">
        <div className="flex-1 flex justify-end pr-1">
          {!up && <div className="h-2 bg-red-400 rounded-l" style={{ width: `${w}%` }} />}
        </div>
        <div className="flex-1 pl-1">
          {up && <div className="h-2 bg-emerald-400 rounded-r" style={{ width: `${w}%` }} />}
        </div>
      </div>
      <span className={`w-16 text-right font-medium ${tone(r.change_pct)}`}>{pct(r.change_pct)}</span>
    </div>
  );
}

export function GrowthPanel() {
  const [period, setPeriod] = useState<"week" | "month">("week");
  const [d, setD] = useState<GrowthData | null>(null);

  useEffect(() => { api.growth(period).then(setD).catch(() => {}); }, [period]);
  if (!d) return null;
  const s = d.summary;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold">Değişim & Büyüme Oranları</h3>
        <div className="flex bg-slate-100 rounded-md p-0.5">
          {(["week", "month"] as const).map((p) => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`text-xs px-2.5 py-1 rounded ${period === p ? "bg-white shadow-sm font-medium" : "text-slate-500"}`}>
              {p === "week" ? "Haftalık" : "Aylık"}
            </button>
          ))}
        </div>
      </div>
      <p className="text-xs text-slate-400 mb-4">Bu dönem vs önceki dönem ({s.period_label})</p>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="border rounded-lg p-3">
          <p className="text-xs text-slate-500">Ciro Değişimi</p>
          <p className={`text-2xl font-bold ${tone(s.revenue_change_pct)}`}>
            {s.revenue_change_pct >= 0 ? "▲" : "▼"} {pct(s.revenue_change_pct)}
          </p>
          <p className="text-xs text-slate-400">{fmt(s.revenue_current)}₺ ← {fmt(s.revenue_previous)}₺</p>
        </div>
        <div className="border rounded-lg p-3">
          <p className="text-xs text-slate-500">Sipariş Değişimi</p>
          <p className={`text-2xl font-bold ${tone(s.orders_change_pct)}`}>
            {s.orders_change_pct >= 0 ? "▲" : "▼"} {pct(s.orders_change_pct)}
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        <div>
          <p className="text-xs font-medium text-slate-500 mb-2">Kanal Bazında</p>
          <div className="space-y-1.5">
            {d.channels.slice(0, 6).map((c) => <Row key={c.name} r={c} label={c.name!} />)}
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-slate-500 mb-2">Kategori Bazında</p>
          <div className="space-y-1.5">
            {d.categories.map((c) => <Row key={c.name} r={c} label={c.name!} />)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-5 mt-4 pt-4 border-t">
        <div>
          <p className="text-xs font-medium text-emerald-600 mb-1.5">📈 En Çok Büyüyen SKU</p>
          {d.top_growing.map((x) => (
            <div key={x.sku} className="flex justify-between text-sm py-0.5">
              <span className="text-slate-600">{x.sku}</span>
              <span className={`font-medium ${tone(x.change_pct)}`}>{pct(x.change_pct)}</span>
            </div>
          ))}
        </div>
        <div>
          <p className="text-xs font-medium text-red-600 mb-1.5">📉 En Çok Küçülen SKU</p>
          {d.top_shrinking.map((x) => (
            <div key={x.sku} className="flex justify-between text-sm py-0.5">
              <span className="text-slate-600">{x.sku}</span>
              <span className={`font-medium ${tone(x.change_pct)}`}>{pct(x.change_pct)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
