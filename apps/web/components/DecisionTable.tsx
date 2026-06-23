"use client";
import { useEffect, useState } from "react";
import { api, type DecisionSummary, type SkuDecision } from "@/lib/api";

const sevDot: Record<string, string> = {
  critical: "bg-red-500", warning: "bg-amber-500", info: "bg-green-500",
};

function scoreColor(s: number) {
  if (s >= 70) return "text-green-600";
  if (s >= 40) return "text-amber-600";
  return "text-red-600";
}

const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");

export function DecisionTable() {
  const [summary, setSummary] = useState<DecisionSummary | null>(null);
  const [items, setItems] = useState<SkuDecision[]>([]);

  useEffect(() => {
    api.decisions().then((d) => { setSummary(d.summary); setItems(d.items); }).catch(() => {});
  }, []);

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold mb-1">Karar Skoru & SKU Kârlılığı</h3>
      <p className="text-xs text-slate-400 mb-4">
        (Kâr Potansiyeli × Güven) − Stok Riski − Müşteri Kaybı − Reklam İsrafı
      </p>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <Stat label="Net Kâr (30g)" value={`${fmt(summary.total_profit)}₺`}
            tone={summary.total_profit >= 0 ? "good" : "bad"} />
          <Stat label="Ort. Marj" value={`%${summary.avg_margin}`}
            tone={summary.avg_margin >= 10 ? "good" : "bad"} />
          <Stat label="Zararlı SKU" value={`${summary.loss_making_skus}/${summary.total_skus}`}
            tone={summary.loss_making_skus ? "bad" : "good"} />
          <Stat label="Stok Riski" value={`${summary.stock_risk_skus}`}
            tone={summary.stock_risk_skus ? "warn" : "good"} />
          <Stat label="Müşteri Terk" value={`%${summary.customer_churn_pct}`}
            tone={summary.customer_churn_pct > 15 ? "warn" : "good"} />
        </div>
      )}

      <div className="overflow-auto max-h-[460px]">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400 text-xs sticky top-0 bg-white">
            <tr>
              <th className="py-2 pr-2">SKU / Kategori</th>
              <th className="py-2 px-2 text-right">Adet</th>
              <th className="py-2 px-2 text-right">Net Satış</th>
              <th className="py-2 px-2 text-right">Kâr</th>
              <th className="py-2 px-2 text-right">Marj</th>
              <th className="py-2 px-2 text-right">Skor</th>
              <th className="py-2 pl-2">Öneri</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.sku} className="border-t hover:bg-slate-50">
                <td className="py-2 pr-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${sevDot[it.severity]}`} />
                    <span className="font-medium">{it.sku}</span>
                    <span className="text-xs text-slate-400">{it.category}</span>
                  </div>
                </td>
                <td className="py-2 px-2 text-right">{fmt(it.units)}</td>
                <td className="py-2 px-2 text-right">{fmt(it.net_sales)}₺</td>
                <td className={`py-2 px-2 text-right font-medium ${it.profit >= 0 ? "text-slate-700" : "text-red-600"}`}>
                  {fmt(it.profit)}₺
                </td>
                <td className={`py-2 px-2 text-right ${it.margin >= 0 ? "text-slate-600" : "text-red-600"}`}>
                  %{it.margin}
                </td>
                <td className={`py-2 px-2 text-right font-bold ${scoreColor(it.decision_score)}`}>
                  {it.decision_score}
                </td>
                <td className="py-2 pl-2 text-xs text-slate-600 max-w-[260px]">{it.recommendation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone: "good" | "bad" | "warn" }) {
  const c = tone === "good" ? "text-green-600" : tone === "warn" ? "text-amber-600" : "text-red-600";
  return (
    <div className="border rounded-lg p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-bold ${c}`}>{value}</p>
    </div>
  );
}
