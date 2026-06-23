"use client";
import { useEffect, useState } from "react";
import { api, type PricingItem } from "@/lib/api";

const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");

export function PricingTable() {
  const [items, setItems] = useState<PricingItem[]>([]);
  const [uplift, setUplift] = useState(0);
  const [sku, setSku] = useState<string>("");
  const [pct, setPct] = useState(4);
  const [sim, setSim] = useState<{ units_change_pct: number; profit_delta: number; elasticity: number } | null>(null);

  useEffect(() => {
    api.pricing().then((d) => {
      setItems(d.items); setUplift(d.summary.total_uplift);
      if (d.items[0]) setSku(d.items[0].sku);
    }).catch(() => {});
  }, []);

  async function runSim(s: string, p: number) {
    const r = await api.simulate(s, p);
    setSim({ units_change_pct: r.simulated.units_change_pct,
      profit_delta: r.simulated.profit_delta, elasticity: r.elasticity });
  }
  useEffect(() => { if (sku) runSim(sku, pct).catch(() => {}); }, [sku, pct]);

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold mb-1">Fiyat Elastikiyeti & "Ya Şöyle Olursa?" Simülatörü</h3>
      <p className="text-xs text-slate-400 mb-4">
        Toplam fiyat optimizasyonu fırsatı: <span className="font-bold text-green-700">{fmt(uplift)}₺</span>
      </p>

      {/* Simülatör */}
      <div className="bg-slate-50 border rounded-lg p-3 mb-4">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <select value={sku} onChange={(e) => setSku(e.target.value)}
            className="border rounded px-2 py-1 text-sm">
            {items.map((i) => <option key={i.sku} value={i.sku}>{i.sku} · {i.category}</option>)}
          </select>
          <div className="flex items-center gap-1">
            {[-10, -4, 4, 10, 20].map((p) => (
              <button key={p} onClick={() => setPct(p)}
                className={`text-xs px-2 py-1 rounded border ${pct === p ? "bg-slate-900 text-white" : ""}`}>
                {p > 0 ? `+%${p}` : `%${p}`}
              </button>
            ))}
          </div>
        </div>
        {sim && (
          <p className="text-sm">
            <span className="text-slate-500">E={sim.elasticity} → </span>
            <span className="font-medium">%{Math.abs(pct)} {pct > 0 ? "zam" : "indirim"}:</span>{" "}
            satış <span className={sim.units_change_pct < 0 ? "text-red-600" : "text-green-600"}>
              %{Math.abs(sim.units_change_pct)} {sim.units_change_pct < 0 ? "düşer" : "artar"}</span>,{" "}
            kâr <span className={`font-bold ${sim.profit_delta >= 0 ? "text-green-600" : "text-red-600"}`}>
              {sim.profit_delta >= 0 ? "+" : ""}{fmt(sim.profit_delta)}₺</span>
          </p>
        )}
      </div>

      {/* Öneri tablosu */}
      <div className="overflow-auto max-h-[320px]">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400 text-xs sticky top-0 bg-white">
            <tr>
              <th className="py-2 pr-2">SKU</th>
              <th className="py-2 px-2 text-right">Fiyat</th>
              <th className="py-2 px-2 text-right">Rakip</th>
              <th className="py-2 px-2 text-right">Elastikiyet</th>
              <th className="py-2 pl-2">Öneri</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.sku} className="border-t hover:bg-slate-50">
                <td className="py-2 pr-2 font-medium">{it.sku}</td>
                <td className="py-2 px-2 text-right">{fmt(it.price)}₺</td>
                <td className="py-2 px-2 text-right text-slate-400">
                  {it.competitor_price ? `${fmt(it.competitor_price)}₺` : "—"}</td>
                <td className="py-2 px-2 text-right">{it.elasticity}</td>
                <td className="py-2 pl-2 text-xs text-slate-600 max-w-[260px]">{it.verdict}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
