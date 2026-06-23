"use client";
import { useEffect, useState } from "react";
import { api, type CustomerOverview } from "@/lib/api";

const segColor: Record<string, string> = {
  vip: "bg-purple-100 text-purple-700", repeat: "bg-green-100 text-green-700",
  new: "bg-blue-100 text-blue-700", at_risk: "bg-red-100 text-red-700",
};
const segLabel: Record<string, string> = {
  vip: "VIP", repeat: "Tekrar", new: "Yeni", at_risk: "Terk Riski",
};
const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");

export function CustomerPanel() {
  const [d, setD] = useState<CustomerOverview | null>(null);
  useEffect(() => { api.customers().then(setD).catch(() => {}); }, []);
  if (!d?.summary) return null;
  const total = d.summary.total_customers;

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold mb-1">Müşteri Değeri & Terk Riski</h3>
      <p className="text-xs text-slate-400 mb-4">LTV · tekrar oranı · segment · terk</p>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <Stat label="Müşteri" value={fmt(total)} />
        <Stat label="Ort. LTV" value={`${fmt(d.summary.avg_ltv)}₺`} />
        <Stat label="Terk" value={`%${d.summary.churn_pct}`}
          tone={d.summary.churn_pct > 15 ? "bad" : "good"} />
      </div>

      <div className="space-y-1.5 mb-4">
        {d.segments.map((s) => (
          <div key={s.segment} className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded ${segColor[s.segment] || "bg-slate-100"}`}>
              {segLabel[s.segment] || s.segment}
            </span>
            <div className="flex-1 bg-slate-100 rounded h-2 overflow-hidden">
              <div className="h-2 bg-slate-400" style={{ width: `${(s.count / total) * 100}%` }} />
            </div>
            <span className="text-xs text-slate-500 w-10 text-right">{s.count}</span>
          </div>
        ))}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
        <p className="text-xs text-amber-800">💡 {d.summary.recommendation}</p>
      </div>

      <p className="text-xs font-medium text-slate-500 mb-1">En Değerli Müşteriler (LTV)</p>
      <div className="overflow-auto max-h-[160px]">
        <table className="w-full text-sm">
          <tbody>
            {d.top_customers.map((c) => (
              <tr key={c.external_id} className="border-t">
                <td className="py-1.5 font-medium">{c.external_id}</td>
                <td className="py-1.5 text-xs text-slate-400">{c.city}</td>
                <td className="py-1.5 text-xs">{c.orders} sip.</td>
                <td className="py-1.5 text-right font-medium">{fmt(c.ltv)}₺</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  const c = tone === "good" ? "text-green-600" : tone === "bad" ? "text-red-600" : "text-slate-700";
  return (
    <div className="border rounded-lg p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-bold ${c}`}>{value}</p>
    </div>
  );
}
